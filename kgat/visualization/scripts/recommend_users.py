#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generate Top-K recommendations for specified users using a trained KGAT checkpoint.

Notes for this repo:
- Internal user node id = raw_user_id + n_entities (see DataLoaderKGAT.construct_data)
- Items are in [0, n_items)
- For prediction, graph must have g.edata['att'] set (compute_attention first)
"""

import argparse
import os
import sys
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import torch

# Ensure repo root is on sys.path when running as a script (python scripts/xxx.py).
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from model.KGAT import KGAT
from utility.helper import load_model
from utility.loader_kgat import DataLoaderKGAT


class _DummyLogger:
    def info(self, *args, **kwargs):  # noqa: D401
        # DataLoaderKGAT expects logging.info; keep silent by default.
        return None


def _parse_users(users_arg: str) -> List[int]:
    users_arg = users_arg.strip()
    if not users_arg:
        return []
    out: List[int] = []
    for part in users_arg.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            lo_s, hi_s = part.split("-", 1)
            lo, hi = int(lo_s), int(hi_s)
            if hi < lo:
                lo, hi = hi, lo
            out.extend(list(range(lo, hi + 1)))
        else:
            out.append(int(part))
    return sorted(list(dict.fromkeys(out)))


@dataclass
class RecRow:
    raw_user: int
    user_node: int
    rank: int
    item: int
    score: float
    item_pop: int


def _build_item_pop(cf_train_items: np.ndarray, n_items: int) -> np.ndarray:
    pop = np.zeros(n_items, dtype=np.int64)
    vals, cnts = np.unique(cf_train_items, return_counts=True)
    pop[vals] = cnts
    return pop


def _topk_for_user(
    scores: torch.Tensor,
    seen_items: np.ndarray,
    k: int,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    scores: (n_items,) on CPU
    seen_items: np.ndarray[int] items interacted in train
    Returns (top_items, top_scores) as numpy arrays, both shape (k,)
    """
    scores = scores.clone()
    if seen_items is not None and len(seen_items) > 0:
        seen = torch.from_numpy(seen_items.astype(np.int64))
        scores[seen] = -1e15
    top_scores, top_items = torch.topk(scores, k=k, largest=True)
    return top_items.cpu().numpy().astype(np.int64), top_scores.cpu().numpy().astype(np.float32)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model_path", required=True, help="Path to model_epoch*.pth")
    ap.add_argument("--data_name", default="amazon-book", help="Dataset name, e.g. amazon-book")
    ap.add_argument("--data_dir", default=None, help="Datasets directory (defaults to <repo_root>/datasets)")
    ap.add_argument("--users", default="0-10", help="User ids, e.g. '0-10' or '0,1,2,10' or '0-3,8,10'")
    ap.add_argument("--topk", type=int, default=20, help="Top-K per user")
    ap.add_argument("--out", default=None, help="Output TSV path (defaults to <repo_root>/outputs/recs_user0_10.tsv)")
    ap.add_argument("--device", default="cuda", choices=["cuda", "cpu"], help="Device to run")
    args2 = ap.parse_args()

    users = _parse_users(args2.users)
    if not users:
        raise SystemExit("Empty --users")

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    model_path = args2.model_path
    if not os.path.isabs(model_path):
        model_path = os.path.join(repo_root, model_path)

    data_dir = args2.data_dir or os.path.join(repo_root, "datasets")

    # Construct an args object equivalent to utility/parser_kgat.py defaults,
    # but without parsing sys.argv (which would conflict with this script).
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
        K=args2.topk,
        build_kg_dict=0,
    )
    kgat_args.save_dir = os.path.join(
        repo_root,
        "trained_model",
        "KGAT",
        kgat_args.data_name,
        f"entitydim{kgat_args.entity_dim}_relationdim{kgat_args.relation_dim}_{kgat_args.aggregation_type}_"
        f"{'-'.join([str(i) for i in eval(kgat_args.conv_dim_list)])}_lr{kgat_args.lr}_pretrain{kgat_args.use_pretrain}",
    )

    use_cuda = (args2.device == "cuda") and torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    # Data
    data = DataLoaderKGAT(kgat_args, logging=_DummyLogger())
    n_items = data.n_items
    item_ids = torch.arange(n_items, dtype=torch.long, device=device)
    item_pop = _build_item_pop(data.cf_train_data[1], n_items)

    # Model
    # NOTE: We don't need to pass pretrain embeddings because checkpoint overwrites weights anyway.
    model = KGAT(kgat_args, data.n_users, data.n_entities, data.n_relations)
    model = load_model(model, kgat_args.pretrain_model_path)
    model.to(device)
    model.eval()

    # Graph + attention
    train_graph = data.train_graph.to(device) if use_cuda else data.train_graph
    with torch.no_grad():
        att = model("calc_att", train_graph)
    train_graph.edata["att"] = att

    # Recommend
    rec_rows: List[RecRow] = []
    # Map raw user ids -> internal node ids
    for raw_u in users:
        user_node = raw_u + data.n_entities
        if user_node not in data.train_user_dict:
            # still can score, but has no train history to filter
            seen_items = np.array([], dtype=np.int64)
        else:
            seen_items = data.train_user_dict[user_node].astype(np.int64)

        user_ids = torch.tensor([user_node], dtype=torch.long, device=device)
        with torch.no_grad():
            score_vec = model("predict", train_graph, user_ids, item_ids).squeeze(0).detach().cpu()

        top_items, top_scores = _topk_for_user(score_vec, seen_items, k=args2.topk)
        for r, (it, sc) in enumerate(zip(top_items, top_scores), start=1):
            rec_rows.append(
                RecRow(
                    raw_user=raw_u,
                    user_node=user_node,
                    rank=r,
                    item=int(it),
                    score=float(sc),
                    item_pop=int(item_pop[it]),
                )
            )

    # Write TSV
    out_path = args2.out or os.path.join(repo_root, "outputs", "recs_user0_10.tsv")
    if not os.path.isabs(out_path):
        out_path = os.path.join(repo_root, out_path)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("raw_user\tuser_node\trank\titem\tscore\titem_pop_train\n")
        for row in rec_rows:
            f.write(
                f"{row.raw_user}\t{row.user_node}\t{row.rank}\t{row.item}\t{row.score:.6f}\t{row.item_pop}\n"
            )

    print(f"[OK] wrote: {out_path}")
    print(f"[INFO] n_items={n_items}, n_entities={data.n_entities}, n_users={data.n_users}")


if __name__ == "__main__":
    main()


