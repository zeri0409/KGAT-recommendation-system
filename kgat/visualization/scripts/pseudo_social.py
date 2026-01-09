import argparse
import math
import os
import random
from collections import defaultdict
from itertools import combinations

import networkx as nx


def read_user_item(file_path):
    """读取 user-物品交互；返回 user->items, item->users, 基本统计。"""
    user_items = defaultdict(list)
    item_users = defaultdict(list)
    max_user = -1
    max_item = -1

    with open(file_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) <= 1:
                continue
            u = int(parts[0])
            items = [int(x) for x in parts[1:]]
            max_user = max(max_user, u)
            max_item = max(max_item, max(items))
            user_items[u].extend(items)
            for it in items:
                item_users[it].append(u)

    return user_items, item_users, max_user + 1, max_item + 1


def build_cooc_edges(item_users, max_users_per_item, min_co):
    """共现法：同一物品的用户两两连边，边权=共同交互次数。"""
    co_counts = defaultdict(int)
    for users in item_users.values():
        if max_users_per_item and len(users) > max_users_per_item:
            users = users[:max_users_per_item]
        uniq_users = sorted(set(users))
        for u, v in combinations(uniq_users, 2):
            co_counts[(u, v)] += 1
    co_counts = {k: v for k, v in co_counts.items() if v >= min_co}
    return co_counts


def build_cosine_edges(co_counts, user_items, topk):
    """相似度法：余弦相似度 = 共现次数 / sqrt(deg_u * deg_v)。"""
    user_deg = {u: len(set(items)) for u, items in user_items.items()}
    cos_edges = defaultdict(float)

    for (u, v), c in co_counts.items():
        denom = math.sqrt(user_deg.get(u, 1) * user_deg.get(v, 1))
        if denom == 0:
            continue
        cos_edges[(u, v)] = c / denom

    if topk is None:
        return cos_edges

    nbrs = defaultdict(list)
    for (u, v), w in cos_edges.items():
        nbrs[u].append((v, w))
        nbrs[v].append((u, w))

    kept = {}
    for u, lst in nbrs.items():
        lst.sort(key=lambda x: x[1], reverse=True)
        for v, w in lst[:topk]:
            key = (u, v) if u < v else (v, u)
            kept[key] = max(kept.get(key, 0), w)
    return kept


def sample_edges(edges, max_users, mode, seed=42):
    """对用户集合抽样，仅保留 sampled 用户之间的边。"""
    if max_users is None or max_users <= 0:
        return edges

    users = set()
    for u, v in edges.keys():
        users.add(u)
        users.add(v)
    if len(users) <= max_users:
        return edges

    random.seed(seed)

    if mode == "random":
        sampled = set(random.sample(list(users), max_users))
    elif mode == "top_degree":
        deg = defaultdict(float)
        for (u, v), w in edges.items():
            deg[u] += float(w)
            deg[v] += float(w)
        top = sorted(deg.items(), key=lambda x: x[1], reverse=True)[:max_users]
        sampled = set(u for u, _ in top)
    else:
        raise ValueError("sample_mode must be one of [random, top_degree]")

    filtered = {(u, v): w for (u, v), w in edges.items() if u in sampled and v in sampled}
    return filtered


def write_edge_files(edges, out_csv, out_gexf, edge_kind):
    """edge_kind 标记边来源（cooc / cosine），避免与 GEXF 保留字段冲突。"""
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)
    with open(out_csv, "w") as f:
        f.write("Source,Target,Weight,Kind\n")
        for (u, v), w in edges.items():
            f.write(f"{u},{v},{w},{edge_kind}\n")

    G = nx.Graph()
    G.graph["mode"] = "static"
    G.graph["defaultedgetype"] = "undirected"
    # 为了让 Gephi 识别边属性，先定义 attribute 列表
    G.graph["edge_default"] = {}
    for (u, v), w in edges.items():
        G.add_edge(u, v, weight=float(w), kind=edge_kind)
    nx.write_gexf(G, out_gexf)


def main():
    parser = argparse.ArgumentParser(description="构造伪社交关系并导出 GEXF/CSV")
    parser.add_argument(
        "--train_file",
        type=str,
        default="datasets/amazon-book/train1.txt",
        help="用户-物品交互文件（与 main_kgat 使用的格式一致）",
    )
    parser.add_argument(
        "--out_dir",
        type=str,
        default="outputs/pseudo_social",
        help="输出目录，含 CSV 与 GEXF",
    )
    parser.add_argument(
        "--max_users_per_item",
        type=int,
        default=80,
        help="单个物品参与共现计算的最多用户数（截断防爆炸，0 关闭）",
    )
    parser.add_argument(
        "--min_co",
        type=int,
        default=2,
        help="共现次数下限，低于该值的边将被过滤",
    )
    parser.add_argument(
        "--topk_cosine",
        type=int,
        default=30,
        help="每个用户保留余弦相似度最高的前 K 个邻居（0 表示不过滤）",
    )
    parser.add_argument(
        "--max_users",
        type=int,
        default=0,
        help="可视化抽样的最大用户数（0 或负数表示不过滤）",
    )
    parser.add_argument(
        "--sample_mode",
        type=str,
        default="top_degree",
        choices=["top_degree", "random"],
        help="抽样策略：top_degree 按边权度排序取前 max_users；random 随机取",
    )
    parser.add_argument(
        "--sample_seed",
        type=int,
        default=42,
        help="random 抽样的随机种子",
    )
    args = parser.parse_args()

    user_items, item_users, n_users, n_items = read_user_item(args.train_file)
    print(f"Loaded interactions: users={n_users}, items={n_items}, edges={len(item_users)} items.")

    co_counts = build_cooc_edges(
        item_users,
        max_users_per_item=args.max_users_per_item if args.max_users_per_item > 0 else None,
        min_co=args.min_co,
    )
    print(f"Co-occurrence edges: {len(co_counts)} (min_co={args.min_co}).")

    cos_edges = build_cosine_edges(
        co_counts,
        user_items,
        topk=None if args.topk_cosine == 0 else args.topk_cosine,
    )
    print(f"Cosine-sim edges: {len(cos_edges)} (topk={args.topk_cosine}).")

    co_vis = sample_edges(co_counts, args.max_users, args.sample_mode, args.sample_seed)
    cos_vis = sample_edges(cos_edges, args.max_users, args.sample_mode, args.sample_seed)
    if args.max_users and args.max_users > 0:
        print(f"[sample] cooc edges -> {len(co_vis)}, cosine edges -> {len(cos_vis)} using mode={args.sample_mode}, max_users={args.max_users}")

    co_csv = os.path.join(args.out_dir, "cooc_edge_list.csv")
    co_gexf = os.path.join(args.out_dir, "cooc_graph.gexf")
    write_edge_files(co_vis, co_csv, co_gexf, "cooc")

    cos_csv = os.path.join(args.out_dir, "cosine_edge_list.csv")
    cos_gexf = os.path.join(args.out_dir, "cosine_graph.gexf")
    write_edge_files(cos_vis, cos_csv, cos_gexf, "cosine")

    print(f"Saved co-occurrence to: {co_csv}, {co_gexf}")
    print(f"Saved cosine-sim to: {cos_csv}, {cos_gexf}")


if __name__ == "__main__":
    main()
