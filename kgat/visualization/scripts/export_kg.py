#!/usr/bin/env python
"""导出 KG+用户/商品 的 GEXF/CSV 可视化文件（独立版本，不依赖 parse_kgat_args）。"""
import argparse
import os
import random
from collections import defaultdict

import networkx as nx
import pandas as pd


def detect_node_type(node_id, n_entities, n_items):
    """区分节点类型：user / item / entity。"""
    if node_id >= n_entities:
        return "user"
    if node_id < n_items:
        return "item"
    return "entity"


def sample_nodes(edges, max_nodes, seed=42):
    """节点抽样：仅保留抽中的节点及其内部边。"""
    if max_nodes is None or max_nodes <= 0:
        return edges
    nodes = set()
    for h, t, _ in edges:
        nodes.add(h)
        nodes.add(t)
    if len(nodes) <= max_nodes:
        return edges
    random.seed(seed)
    keep = set(random.sample(list(nodes), max_nodes))
    return [(h, t, r) for h, t, r in edges if h in keep and t in keep]


def load_cf(file_path):
    """读取用户-商品交互文件，返回 (user_ids, item_ids) 元组列表。"""
    pairs = []
    with open(file_path, "r") as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) <= 1:
                continue
            u = int(parts[0])
            for it in parts[1:]:
                pairs.append((u, int(it)))
    return pairs


def main():
    parser = argparse.ArgumentParser(description="导出 KG+用户/商品 的 GEXF/CSV 可视化文件")
    parser.add_argument("--data_dir", type=str, default="datasets/amazon-book", help="数据集目录")
    parser.add_argument("--out_dir", type=str, default="outputs/kg_export", help="输出目录")
    parser.add_argument("--max_nodes", type=int, default=20000, help="抽样保留的节点数（0 或负数表示不过滤）")
    parser.add_argument("--sample_seed", type=int, default=42, help="节点抽样随机种子")
    parser.add_argument("--only_interactions", action="store_true", help="仅导出用户-物品交互边（不含实体关系）")
    args = parser.parse_args()

    train_file = os.path.join(args.data_dir, "train.txt")
    kg_file = os.path.join(args.data_dir, "kg_final.txt")

    # 读取 CF 数据获取 n_users, n_items
    cf_pairs = load_cf(train_file)
    n_users = max(u for u, _ in cf_pairs) + 1
    n_items = max(it for _, it in cf_pairs) + 1
    print(f"n_users={n_users}, n_items={n_items}")

    # 读取 KG 数据获取 n_entities
    kg_data = pd.read_csv(kg_file, sep=" ", names=["h", "r", "t"], engine="python")
    kg_data = kg_data.drop_duplicates()
    n_entities = max(kg_data["h"].max(), kg_data["t"].max()) + 1
    n_relations_orig = kg_data["r"].max() + 1
    print(f"n_entities={n_entities}, n_relations_orig={n_relations_orig}")

    # 按 KGAT 方式构建 CKG：反向三元组 + 关系偏移 + 用户 ID 偏移 + 交互边
    reverse_kg = kg_data.copy()
    reverse_kg = reverse_kg.rename({"h": "t", "t": "h"}, axis="columns")
    reverse_kg["r"] += n_relations_orig
    kg_data = pd.concat([kg_data, reverse_kg], ignore_index=True)
    kg_data["r"] += 2  # 空出 0/1 给交互边

    # 用户 ID 偏移
    cf_train = [(u + n_entities, it) for u, it in cf_pairs]
    # 交互边：r=0 用户->商品，r=1 商品->用户
    cf_edges = [(u, it, 0) for u, it in cf_train] + [(it, u, 1) for u, it in cf_train]

    if args.only_interactions:
        edges = cf_edges
    else:
        kg_edges = [(int(h), int(t), int(r)) for h, r, t in kg_data.values]
        edges = kg_edges + cf_edges

    print(f"Total edges before sampling: {len(edges)}")
    edges = sample_nodes(edges, args.max_nodes, args.sample_seed)
    print(f"Export edges: {len(edges)} (max_nodes={args.max_nodes})")

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, "kg_edge_list.csv")
    gexf_path = os.path.join(args.out_dir, "kg_graph.gexf")

    with open(csv_path, "w") as f:
        f.write("Source,Target,Rel,Type\n")
        for h, t, r in edges:
            f.write(f"{h},{t},{r},kg\n")

    G = nx.Graph()
    G.graph["mode"] = "static"
    G.graph["defaultedgetype"] = "undirected"
    for h, t, r in edges:
        G.add_edge(h, t, rel=int(r))
        if "ntype" not in G.nodes[h]:
            G.nodes[h]["ntype"] = detect_node_type(h, n_entities, n_items)
        if "ntype" not in G.nodes[t]:
            G.nodes[t]["ntype"] = detect_node_type(t, n_entities, n_items)

    nx.write_gexf(G, gexf_path)
    print(f"Saved CSV to {csv_path}")
    print(f"Saved GEXF to {gexf_path}")


if __name__ == "__main__":
    main()
