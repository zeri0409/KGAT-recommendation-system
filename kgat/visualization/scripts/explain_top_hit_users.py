#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Pick top-N users with the highest hit@K, then explain their Top-M recommendations using:
1) KG short paths with high attention weights (1-3 hops) on the cached CKG graph.
2) Co-occurrence pseudo social neighbors from outputs/pseudo_social_sampled/cooc_edge_list.csv.

Outputs:
- outputs/top_hit_users_top5.tsv
- outputs/top_hit_users_top5_explanations.md
"""

import argparse
import os
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
import torch

# Ensure repo root import works when running as a script.
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dgl import load_graphs  # noqa: E402

from model.KGAT import KGAT  # noqa: E402
from utility.helper import load_model  # noqa: E402
from utility.loader_kgat import DataLoaderKGAT  # noqa: E402


class _DummyLogger:
    def info(self, *args, **kwargs):
        return None


def _read_relation_list(path: str) -> List[str]:
    rels: List[str] = []
    with open(path, "r", encoding="utf-8") as f:
        _ = f.readline()
        for line in f:
            line = line.strip()
            if not line:
                continue
            org, remap = line.split()
            rels.append(org)
    return rels


def _read_item_map(path: str, needed_items: Optional[set] = None) -> Dict[int, Tuple[str, str]]:
    """
    returns item_id -> (asin, freebase_id)
    """
    out: Dict[int, Tuple[str, str]] = {}
    with open(path, "r", encoding="utf-8") as f:
        _ = f.readline()
        for line in f:
            asin, rid, fid = line.strip().split()
            iid = int(rid)
            if needed_items is None or iid in needed_items:
                out[iid] = (asin, fid)
                if needed_items is not None and len(out) == len(needed_items):
                    break
    return out


def _build_item_pop(cf_train_items: np.ndarray, n_items: int) -> np.ndarray:
    pop = np.zeros(n_items, dtype=np.int64)
    vals, cnts = np.unique(cf_train_items, return_counts=True)
    pop[vals] = cnts
    return pop


def _load_cooc_neighbors(edge_csv: str) -> Dict[int, List[Tuple[int, float]]]:
    """
    cooc_edge_list.csv: Source,Target,Weight,Kind
    Returns raw_user -> list[(neighbor_raw_user, weight)] sorted desc.
    """
    df = pd.read_csv(edge_csv)
    neigh: Dict[int, List[Tuple[int, float]]] = defaultdict(list)
    for s, t, w in zip(df["Source"].astype(int), df["Target"].astype(int), df["Weight"].astype(float)):
        neigh[s].append((t, w))
        neigh[t].append((s, w))
    for u in list(neigh.keys()):
        neigh[u].sort(key=lambda x: x[1], reverse=True)
    return neigh


def _node_label(node_id: int, n_items: int, n_entities: int, item_map: Dict[int, Tuple[str, str]]) -> str:
    if node_id >= n_entities:
        return f"U{node_id - n_entities}"
    if node_id < n_items:
        asin = item_map.get(node_id, (str(node_id), ""))[0]
        return f"I{node_id}({asin})"
    return f"E{node_id}"


def _rel_label(rel_id: int, base_rels: List[str]) -> str:
    """
    Graph relation id mapping (DataLoaderKGAT.construct_data):
    - 0,1 are CF relations
    - base KG relations are shifted by +2, and inverse relations are +2 + n_base
    """
    if rel_id == 0:
        return "cf:item->user"
    if rel_id == 1:
        return "cf:user->item"
    base = rel_id - 2
    n_base = len(base_rels)
    if 0 <= base < n_base:
        return base_rels[base]
    inv = base - n_base
    if 0 <= inv < n_base:
        return base_rels[inv] + " (inv)"
    return f"rel#{rel_id}"


@dataclass
class EdgeInfo:
    dst: int
    rel: int
    att: float


def _top_out_edges(g, node: int, topn: int) -> List[EdgeInfo]:
    src, dst, eids = g.out_edges(node, form="all")
    if len(eids) == 0:
        return []
    rel = g.edata["type"][eids].detach().cpu().numpy().astype(np.int64)
    att = g.edata["att"][eids].detach().cpu().numpy().astype(np.float32)
    dst = dst.detach().cpu().numpy().astype(np.int64)
    order = np.argsort(-att)[:topn]
    return [EdgeInfo(dst=int(dst[i]), rel=int(rel[i]), att=float(att[i])) for i in order]


@dataclass
class Path:
    nodes: List[int]
    rels: List[int]
    atts: List[float]

    @property
    def score(self) -> float:
        # rank by product; add eps to avoid zero
        s = 1.0
        for a in self.atts:
            s *= float(a) + 1e-12
        return s


def _find_paths_u_to_item(
    g,
    u_node: int,
    target_item: int,
    max_hops: int = 3,
    fanout: int = 20,
    max_paths: int = 2,
) -> List[Path]:
    """
    Heuristic limited search using top attention outgoing edges per node.
    Returns up to max_paths paths.
    """
    results: List[Path] = []

    # Hop 1
    lvl1 = _top_out_edges(g, u_node, fanout)
    for e1 in lvl1:
        if e1.dst == target_item:
            results.append(Path(nodes=[u_node, e1.dst], rels=[e1.rel], atts=[e1.att]))
    if results and (max_hops == 1):
        results.sort(key=lambda p: p.score, reverse=True)
        return results[:max_paths]

    if max_hops >= 2:
        for e1 in lvl1:
            lvl2 = _top_out_edges(g, e1.dst, fanout)
            for e2 in lvl2:
                if e2.dst == target_item:
                    results.append(
                        Path(
                            nodes=[u_node, e1.dst, e2.dst],
                            rels=[e1.rel, e2.rel],
                            atts=[e1.att, e2.att],
                        )
                    )
    if results and (max_hops == 2):
        results.sort(key=lambda p: p.score, reverse=True)
        return results[:max_paths]

    if max_hops >= 3:
        for e1 in lvl1:
            lvl2 = _top_out_edges(g, e1.dst, fanout)
            for e2 in lvl2:
                lvl3 = _top_out_edges(g, e2.dst, fanout)
                for e3 in lvl3:
                    if e3.dst == target_item:
                        results.append(
                            Path(
                                nodes=[u_node, e1.dst, e2.dst, e3.dst],
                                rels=[e1.rel, e2.rel, e3.rel],
                                atts=[e1.att, e2.att, e3.att],
                            )
                        )

    results.sort(key=lambda p: p.score, reverse=True)
    # dedupe by node sequence
    seen = set()
    out: List[Path] = []
    for p in results:
        key = tuple(p.nodes)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
        if len(out) >= max_paths:
            break
    return out


def _mask_train_items(scores: torch.Tensor, user_nodes: Sequence[int], train_user_dict: Dict[int, np.ndarray]) -> None:
    """
    In-place mask training positives so they won't be recommended.
    scores: (B, n_items) on GPU/CPU
    """
    for i, u in enumerate(user_nodes):
        seen = train_user_dict.get(int(u))
        if seen is None or len(seen) == 0:
            continue
        idx = torch.as_tensor(seen, dtype=torch.long, device=scores.device)
        scores[i].index_fill_(0, idx, -1e15)


def _hit_count(top_items: Sequence[int], test_items: np.ndarray) -> int:
    if test_items is None or len(test_items) == 0:
        return 0
    return len(set(map(int, top_items)) & set(map(int, test_items)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_path", required=True)
    ap.add_argument("--data_name", default="amazon-book")
    ap.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    ap.add_argument("--eval_k", type=int, default=20, help="Compute hit@K for ranking users")
    ap.add_argument("--top_users", type=int, default=10, help="Pick top-N users by hit@K")
    ap.add_argument("--rec_k", type=int, default=5, help="Show Top-M recs for each selected user")
    ap.add_argument("--batch_size", type=int, default=256)
    ap.add_argument("--cooc_csv", default="outputs/pseudo_social_sampled/cooc_edge_list.csv")
    ap.add_argument("--cooc_topn", type=int, default=5, help="Neighbors to show from cooc graph")
    ap.add_argument("--fanout", type=int, default=20, help="Per-hop fanout for path search")
    ap.add_argument("--max_hops", type=int, default=3)
    args2 = ap.parse_args()

    repo_root = _REPO_ROOT
    model_path = args2.model_path
    if not os.path.isabs(model_path):
        model_path = os.path.join(repo_root, model_path)

    use_cuda = (args2.device == "cuda") and torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    # Construct KGAT args (match parser_kgat defaults)
    data_dir = os.path.join(repo_root, "datasets")
    kgat_args = argparse.Namespace(
        local_rank=0,
        seed=2020,
        data_name=args2.data_name,
        data_dir=data_dir,
        use_graph=1,
        use_pretrain=1,
        pretrain_embedding_dir=os.path.join(repo_root, "datasets", "pretrain"),
        pretrain_model_path=model_path,
        cf_batch_size=1024,
        kg_batch_size=1024,
        test_batch_size=1024,
        entity_dim=64,
        relation_dim=64,
        aggregation_type="bi-interaction",
        conv_dim_list="[64, 32, 16]",
        mess_dropout="[0.1, 0.1, 0.1]",
        kg_l2loss_lambda=1e-5,
        cf_l2loss_lambda=1e-5,
        lr=0.0001,
        n_epoch=0,
        stopping_steps=10,
        cf_print_every=1,
        kg_print_every=1,
        evaluate_every=1,
        K=args2.eval_k,
        build_kg_dict=0,  # critical for speed in inference
    )

    # Load data + cached graph
    data = DataLoaderKGAT(kgat_args, logging=_DummyLogger())
    n_items = data.n_items
    n_entities = data.n_entities

    # Read relation names for explanation
    base_rels = _read_relation_list(os.path.join(data_dir, args2.data_name, "relation_list.txt"))

    item_ids = torch.arange(n_items, dtype=torch.long, device=device)
    item_pop = _build_item_pop(data.cf_train_data[1], n_items)

    # Model
    model = KGAT(kgat_args, data.n_users, data.n_entities, data.n_relations)
    model = load_model(model, model_path)
    model.to(device)
    model.eval()

    # Graph
    train_graph = data.train_graph.to(device) if use_cuda else data.train_graph
    with torch.no_grad():
        att = model("calc_att", train_graph)
    train_graph.edata["att"] = att

    # Compute hit@K for all test users; keep Top-N by hit then by test_pos count
    test_users = np.array(sorted(list(data.test_user_dict.keys())), dtype=np.int64)
    hits: List[Tuple[int, int, int]] = []  # (hit, test_pos, user_node)

    bs = int(args2.batch_size)
    for start in range(0, len(test_users), bs):
        batch_users = test_users[start : start + bs]
        u_tensor = torch.as_tensor(batch_users, dtype=torch.long, device=device)
        with torch.no_grad():
            scores = model("predict", train_graph, u_tensor, item_ids)
        _mask_train_items(scores, batch_users, data.train_user_dict)
        top_scores, top_items = torch.topk(scores, k=args2.eval_k, largest=True)
        top_items = top_items.detach().cpu().numpy()
        for i, u in enumerate(batch_users):
            titems = data.test_user_dict[int(u)]
            hit = _hit_count(top_items[i], titems)
            hits.append((int(hit), int(len(titems)), int(u)))

    hits.sort(key=lambda x: (x[0], x[1]), reverse=True)
    selected = hits[: args2.top_users]

    # cooc neighbors
    cooc_csv = args2.cooc_csv
    if not os.path.isabs(cooc_csv):
        cooc_csv = os.path.join(repo_root, cooc_csv)
    cooc_neigh = _load_cooc_neighbors(cooc_csv) if os.path.exists(cooc_csv) else {}

    # Prepare outputs
    out_tsv = os.path.join(repo_root, "outputs", "top_hit_users_top5.tsv")
    out_md = os.path.join(repo_root, "outputs", "top_hit_users_top5_explanations.md")
    os.makedirs(os.path.dirname(out_tsv), exist_ok=True)

    # For ASIN mapping (only needed items)
    # We'll fill later after collecting items.
    rec_rows = []

    # generate rec_k + explanations
    for rank_u, (hit, test_pos, u_node) in enumerate(selected, start=1):
        raw_u = u_node - n_entities
        # compute top rec_k items
        u_tensor = torch.tensor([u_node], dtype=torch.long, device=device)
        with torch.no_grad():
            score_vec = model("predict", train_graph, u_tensor, item_ids).squeeze(0)
        _mask_train_items(score_vec.unsqueeze(0), [u_node], data.train_user_dict)
        top_scores, top_items = torch.topk(score_vec, k=args2.rec_k, largest=True)
        top_items = top_items.detach().cpu().numpy().astype(np.int64)
        top_scores = top_scores.detach().cpu().numpy().astype(np.float32)

        # cooc neighbors for this raw user
        neigh = cooc_neigh.get(int(raw_u), [])[: args2.cooc_topn]
        neigh_raw = [n for n, _w in neigh]
        neigh_w = {int(n): float(w) for n, w in neigh}

        # how many of those neighbors interacted with each recommended item?
        neigh_train_sets = {}
        for nr in neigh_raw:
            nn = int(nr) + n_entities
            items = data.train_user_dict.get(nn)
            neigh_train_sets[int(nr)] = set(map(int, items)) if items is not None else set()

        test_items_u = set(map(int, data.test_user_dict.get(int(u_node), [])))

        for r, (it, sc) in enumerate(zip(top_items, top_scores), start=1):
            it = int(it)
            paths = _find_paths_u_to_item(
                train_graph,
                u_node=u_node,
                target_item=it,
                max_hops=args2.max_hops,
                fanout=args2.fanout,
                max_paths=2,
            )
            # serialize paths for TSV
            path_strs = []
            for p in paths:
                segs = []
                for j in range(len(p.rels)):
                    segs.append(f"{p.nodes[j]} -[{p.rels[j]}|att={p.atts[j]:.4g}]-> {p.nodes[j+1]}")
                path_strs.append(" ; ".join(segs))
            # neighbor support
            support = []
            for nr in neigh_raw:
                if it in neigh_train_sets.get(int(nr), set()):
                    support.append(str(int(nr)))
            rec_rows.append(
                {
                    "user_rank": rank_u,
                    "raw_user": int(raw_u),
                    "user_node": int(u_node),
                    "hit@K": int(hit),
                    "test_pos": int(test_pos),
                    "rec_rank": int(r),
                    "item": int(it),
                    "score": float(sc),
                    "item_pop_train": int(item_pop[it]),
                    "in_test": int(it in test_items_u),
                    "cooc_neighbors": ",".join([f"{n}:{neigh_w[n]:.0f}" for n in neigh_raw]) if neigh_raw else "",
                    "neighbor_support_users": ",".join(support),
                    "kg_paths": " || ".join(path_strs),
                }
            )

    df_out = pd.DataFrame(rec_rows)
    needed_items = set(df_out["item"].astype(int).tolist())
    item_map = _read_item_map(os.path.join(data_dir, args2.data_name, "item_list.txt"), needed_items=needed_items)
    df_out["asin"] = df_out["item"].map(lambda x: item_map.get(int(x), ("", ""))[0])
    df_out.to_csv(out_tsv, sep="\t", index=False)

    # Markdown report (more readable)
    with open(out_md, "w", encoding="utf-8") as f:
        f.write(f"# Top-{args2.top_users} users by hit@{args2.eval_k} (show Top-{args2.rec_k} recs)\n\n")
        f.write(f"- model: `{os.path.relpath(model_path, repo_root)}`\n")
        f.write(f"- cooc graph: `{os.path.relpath(cooc_csv, repo_root)}`\n")
        f.write(f"- graph cache: `datasets/{args2.data_name}/kgat_dgl_graph.bin`\n\n")

        for u_rank in sorted(df_out["user_rank"].unique()):
            sub_u = df_out[df_out["user_rank"] == u_rank].sort_values("rec_rank")
            raw_u = int(sub_u["raw_user"].iloc[0])
            hit = int(sub_u["hit@K"].iloc[0])
            test_pos = int(sub_u["test_pos"].iloc[0])
            f.write(f"## User {raw_u} (rank#{u_rank}, hit@{args2.eval_k}={hit}, test_pos={test_pos})\n\n")

            neigh_s = str(sub_u["cooc_neighbors"].iloc[0])
            if neigh_s:
                f.write(f"**cooc邻居(top{args2.cooc_topn})**: {neigh_s}\n\n")
            else:
                f.write(f"**cooc邻居(top{args2.cooc_topn})**: (该用户不在pseudo_social_sampled子图中或无边)\n\n")

            f.write("|rank|item_id|ASIN|score|train_pop|in_test|邻居也交互(用户raw_id)|KG高attention路径(最多2条)|\n")
            f.write("|---:|---:|---|---:|---:|:---:|---|---|\n")
            for _, row in sub_u.iterrows():
                paths_txt = row["kg_paths"]
                # decode for readability
                pretty_paths = []
                if isinstance(paths_txt, str) and paths_txt:
                    for p in paths_txt.split(" || "):
                        segs = []
                        for seg in p.split(" ; "):
                            # seg: "node -[rel|att=]-> node"
                            try:
                                left, rest = seg.split(" -[", 1)
                                mid, right = rest.split("]-> ", 1)
                                rel_s, att_s = mid.split("|att=")
                                rel_id = int(rel_s)
                                att_v = float(att_s)
                                left_n = int(left.strip())
                                right_n = int(right.strip())
                                segs.append(
                                    f"{_node_label(left_n, n_items, n_entities, item_map)} "
                                    f"-[{_rel_label(rel_id, base_rels)}; att={att_v:.3g}]-> "
                                    f"{_node_label(right_n, n_items, n_entities, item_map)}"
                                )
                            except Exception:
                                segs.append(seg)
                        pretty_paths.append(" → ".join(segs))
                pretty_paths_s = "<br/>".join(pretty_paths) if pretty_paths else "(未找到≤3跳路径)"

                f.write(
                    f"|{int(row['rec_rank'])}|{int(row['item'])}|{row['asin']}|{float(row['score']):.4f}|"
                    f"{int(row['item_pop_train'])}|{('Y' if int(row['in_test']) else 'N')}|"
                    f"{row['neighbor_support_users'] or '-'}|{pretty_paths_s}|\n"
                )
            f.write("\n")

    print("[OK] wrote:", out_tsv, flush=True)
    print("[OK] wrote:", out_md, flush=True)
    print("[INFO] best hit@K among selected:", int(selected[0][0]) if selected else 0, flush=True)


if __name__ == "__main__":
    main()


