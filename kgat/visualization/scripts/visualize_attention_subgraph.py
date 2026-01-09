#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
KGAT Attention Subgraph Visualization

目标：展示不同邻居节点对目标用户/物品的贡献度（Attention Weights）

可视化内容：
- 子图采样：选取一个具体的 User 节点，展示其 2-hop 内的 Item 和 Entity
- 连边粗细：根据 Attention Score (π) 决定边的粗细，粗边代表该路径对推荐结果贡献大
- 节点颜色：User（红）、Item（蓝）、Entity（绿）

输出：
- edge_list.csv: (Source, Target, Weight, Type)
- attention_subgraph.gexf: 可导入 Gephi 的图文件
"""

import argparse
import os
import sys
from collections import defaultdict
from typing import Dict, List, Set, Tuple

import networkx as nx
import numpy as np
import pandas as pd
import torch

# Ensure repo root import works
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from model.KGAT import KGAT
from utility.helper import load_model
from utility.loader_kgat import DataLoaderKGAT


class _DummyLogger:
    def info(self, *args, **kwargs):
        pass


# 关系ID到可读名称的映射
RELATION_NAMES = {
    0: "cf:item->user",
    1: "cf:user->item",
    2: "type",
    3: "instance",
    4: "copyright_date",
    5: "rdf_type",
    6: "prominent_type",
    7: "subjects",
    8: "first_publication",
    9: "notable_types",
    10: "subject_works",
    11: "genre_books",
    12: "author",
    13: "original_language",
    14: "is_reviewed",
    15: "book_genre",
    16: "author_works",
    17: "previous_in_series",
    18: "series_works",
    19: "character_appears",
    20: "part_of_series",
    21: "characters",
    22: "next_in_series",
}


def get_relation_name(rel_id: int, n_base_relations: int = 39) -> str:
    """
    将图中的关系ID转换为可读名称
    - 0, 1: CF 关系
    - 2 ~ n_base+1: 原始 KG 关系
    - n_base+2 ~ : 逆向 KG 关系
    """
    if rel_id in RELATION_NAMES:
        return RELATION_NAMES[rel_id]
    if rel_id < n_base_relations + 2:
        return f"kg_rel_{rel_id - 2}"
    else:
        return f"kg_rel_{rel_id - 2 - n_base_relations}_inv"


def extract_2hop_subgraph(
    g,
    center_node: int,
    n_items: int,
    n_entities: int,
    max_neighbors_per_hop: int = 50,
) -> Tuple[Set[int], List[Tuple[int, int, int, float]]]:
    """
    提取以 center_node 为中心的 2-hop 子图
    
    返回:
        nodes: 子图中的所有节点
        edges: [(src, dst, rel_type, attention_weight), ...]
    """
    att = g.edata['att'].cpu().numpy().flatten()
    edge_types = g.edata['type'].cpu().numpy().flatten()
    
    nodes = {center_node}
    edges = []
    
    # 1-hop neighbors
    src_1, dst_1, eid_1 = g.out_edges(center_node, form='all')
    src_1 = src_1.cpu().numpy()
    dst_1 = dst_1.cpu().numpy()
    eid_1 = eid_1.cpu().numpy()
    
    # 按 attention 排序，取 top-k
    if len(eid_1) > max_neighbors_per_hop:
        att_1 = att[eid_1]
        topk_idx = np.argsort(-att_1)[:max_neighbors_per_hop]
        eid_1 = eid_1[topk_idx]
        dst_1 = dst_1[topk_idx]
    
    hop1_nodes = set()
    for i, (eid, dst) in enumerate(zip(eid_1, dst_1)):
        dst = int(dst)
        nodes.add(dst)
        hop1_nodes.add(dst)
        edges.append((center_node, dst, int(edge_types[eid]), float(att[eid])))
    
    # 2-hop neighbors
    for hop1_node in hop1_nodes:
        src_2, dst_2, eid_2 = g.out_edges(hop1_node, form='all')
        src_2 = src_2.cpu().numpy()
        dst_2 = dst_2.cpu().numpy()
        eid_2 = eid_2.cpu().numpy()
        
        # 过滤掉已经在 1-hop 中的节点（避免回环到 center）
        mask = ~np.isin(dst_2, [center_node])
        eid_2 = eid_2[mask]
        dst_2 = dst_2[mask]
        
        if len(eid_2) > max_neighbors_per_hop:
            att_2 = att[eid_2]
            topk_idx = np.argsort(-att_2)[:max_neighbors_per_hop]
            eid_2 = eid_2[topk_idx]
            dst_2 = dst_2[topk_idx]
        
        for eid, dst in zip(eid_2, dst_2):
            dst = int(dst)
            nodes.add(dst)
            edges.append((hop1_node, dst, int(edge_types[eid]), float(att[eid])))
    
    return nodes, edges


def get_node_type(node_id: int, n_items: int, n_entities: int) -> str:
    """判断节点类型"""
    if node_id >= n_entities:
        return "User"
    elif node_id < n_items:
        return "Item"
    else:
        return "Entity"


def get_node_color(node_type: str) -> str:
    """返回节点颜色（RGB）"""
    colors = {
        "User": "#E74C3C",     # 红色
        "Item": "#3498DB",     # 蓝色
        "Entity": "#2ECC71",   # 绿色
    }
    return colors.get(node_type, "#95A5A6")


def build_networkx_graph(
    nodes: Set[int],
    edges: List[Tuple[int, int, int, float]],
    n_items: int,
    n_entities: int,
    center_node: int,
    item_asins: Dict[int, str] = None,
) -> nx.DiGraph:
    """构建 NetworkX 图对象"""
    G = nx.DiGraph()
    
    # 添加节点
    for node in nodes:
        node_type = get_node_type(node, n_items, n_entities)
        color = get_node_color(node_type)
        
        # 节点标签
        if node_type == "User":
            label = f"U{node - n_entities}"
        elif node_type == "Item":
            asin = item_asins.get(node, "") if item_asins else ""
            label = f"I{node}" + (f"({asin})" if asin else "")
        else:
            label = f"E{node}"
        
        # 是否为中心节点
        is_center = (node == center_node)
        
        G.add_node(
            node,
            label=label,
            node_type=node_type,
            viz={"color": {"r": int(color[1:3], 16), 
                          "g": int(color[3:5], 16), 
                          "b": int(color[5:7], 16), 
                          "a": 1.0},
                 "size": 30 if is_center else (20 if node_type == "User" else 15)},
        )
    
    # 添加边
    for src, dst, rel_type, att_weight in edges:
        rel_name = get_relation_name(rel_type)
        
        # 边的粗细由 attention weight 决定（放大以便可视化）
        edge_weight = float(att_weight) * 100  # 放大 100 倍便于显示
        
        G.add_edge(
            src, dst,
            weight=edge_weight,
            attention=float(att_weight),
            relation=rel_name,
            rel_type=rel_type,
            label=rel_name,
        )
    
    return G


def load_item_asins(item_list_path: str, items: Set[int]) -> Dict[int, str]:
    """加载物品 ASIN"""
    asins = {}
    with open(item_list_path, 'r') as f:
        _ = f.readline()
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                asin, iid = parts[0], int(parts[1])
                if iid in items:
                    asins[iid] = asin
    return asins


def main():
    parser = argparse.ArgumentParser(description="KGAT Attention Subgraph Visualization")
    parser.add_argument("--model_path", required=True, help="Path to trained model .pth file")
    parser.add_argument("--user", type=int, required=True, help="Raw user ID to visualize (0-based)")
    parser.add_argument("--data_name", default="amazon-book")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--max_neighbors", type=int, default=30, help="Max neighbors per hop")
    parser.add_argument("--output_dir", default=None, help="Output directory (default: outputs/attention_viz)")
    args = parser.parse_args()
    
    print(f"[INFO] Visualizing 2-hop attention subgraph for User {args.user}", flush=True)
    
    repo_root = _REPO_ROOT
    model_path = args.model_path
    if not os.path.isabs(model_path):
        model_path = os.path.join(repo_root, model_path)
    
    use_cuda = (args.device == "cuda") and torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")
    
    # 构建 KGAT args
    data_dir = os.path.join(repo_root, "datasets")
    kgat_args = argparse.Namespace(
        local_rank=0, seed=2020, data_name=args.data_name, data_dir=data_dir,
        use_graph=1, use_pretrain=1,
        pretrain_embedding_dir=os.path.join(repo_root, "datasets", "pretrain"),
        pretrain_model_path=model_path,
        cf_batch_size=1024, kg_batch_size=1024, test_batch_size=1024,
        entity_dim=64, relation_dim=64, aggregation_type="bi-interaction",
        conv_dim_list="[64, 32, 16]", mess_dropout="[0.1, 0.1, 0.1]",
        kg_l2loss_lambda=1e-5, cf_l2loss_lambda=1e-5, lr=0.0001,
        n_epoch=0, stopping_steps=10, cf_print_every=1, kg_print_every=1, 
        evaluate_every=1, K=20, build_kg_dict=0,
    )
    
    # 加载数据
    print("[INFO] Loading data...", flush=True)
    data = DataLoaderKGAT(kgat_args, logging=_DummyLogger())
    n_items = data.n_items
    n_entities = data.n_entities
    
    # 将 raw_user 转换为内部节点 ID
    user_node = args.user + n_entities
    print(f"[INFO] User {args.user} -> internal node {user_node}", flush=True)
    print(f"[INFO] n_items={n_items}, n_entities={n_entities}", flush=True)
    
    # 加载模型
    print("[INFO] Loading model...", flush=True)
    model = KGAT(kgat_args, data.n_users, data.n_entities, data.n_relations)
    model = load_model(model, model_path)
    model.to(device)
    model.eval()
    
    # 计算 attention
    print("[INFO] Computing attention weights...", flush=True)
    train_graph = data.train_graph.to(device) if use_cuda else data.train_graph
    with torch.no_grad():
        att = model("calc_att", train_graph)
    train_graph.edata["att"] = att
    
    # 提取 2-hop 子图
    print(f"[INFO] Extracting 2-hop subgraph (max {args.max_neighbors} neighbors/hop)...", flush=True)
    nodes, edges = extract_2hop_subgraph(
        train_graph, user_node, n_items, n_entities, 
        max_neighbors_per_hop=args.max_neighbors
    )
    print(f"[INFO] Subgraph: {len(nodes)} nodes, {len(edges)} edges", flush=True)
    
    # 统计节点类型
    type_counts = defaultdict(int)
    for n in nodes:
        type_counts[get_node_type(n, n_items, n_entities)] += 1
    print(f"[INFO] Node types: {dict(type_counts)}", flush=True)
    
    # 加载 ASIN
    items_in_subgraph = {n for n in nodes if n < n_items}
    item_asins = load_item_asins(
        os.path.join(data_dir, args.data_name, "item_list.txt"),
        items_in_subgraph
    )
    
    # 构建 NetworkX 图
    print("[INFO] Building NetworkX graph...", flush=True)
    G = build_networkx_graph(nodes, edges, n_items, n_entities, user_node, item_asins)
    
    # 输出目录
    output_dir = args.output_dir or os.path.join(repo_root, "outputs", "attention_viz")
    os.makedirs(output_dir, exist_ok=True)
    
    # 导出 edge_list.csv
    edge_df = pd.DataFrame([
        {
            "Source": src,
            "Target": dst,
            "Weight": att_weight,
            "Type": get_relation_name(rel_type),
            "RelType": rel_type,
        }
        for src, dst, rel_type, att_weight in edges
    ])
    edge_csv_path = os.path.join(output_dir, f"user{args.user}_edge_list.csv")
    edge_df.to_csv(edge_csv_path, index=False)
    print(f"[OK] Saved: {edge_csv_path}", flush=True)
    
    # 导出节点列表
    node_df = pd.DataFrame([
        {
            "Id": n,
            "Label": G.nodes[n]["label"],
            "NodeType": G.nodes[n]["node_type"],
        }
        for n in G.nodes()
    ])
    node_csv_path = os.path.join(output_dir, f"user{args.user}_node_list.csv")
    node_df.to_csv(node_csv_path, index=False)
    print(f"[OK] Saved: {node_csv_path}", flush=True)
    
    # 导出 .gexf 格式
    gexf_path = os.path.join(output_dir, f"user{args.user}_attention_subgraph.gexf")
    nx.write_gexf(G, gexf_path)
    print(f"[OK] Saved: {gexf_path}", flush=True)
    
    # 打印 attention 统计
    att_values = [e[3] for e in edges]
    print("\n📈 Attention 统计:", flush=True)
    print(f"   - Min: {min(att_values):.6f}", flush=True)
    print(f"   - Max: {max(att_values):.6f}", flush=True)
    print(f"   - Mean: {np.mean(att_values):.6f}", flush=True)
    print(f"   - Median: {np.median(att_values):.6f}", flush=True)
    
    # 打印 Top-10 高 attention 边
    print("\n🔝 Top-10 高 Attention 边:", flush=True)
    sorted_edges = sorted(edges, key=lambda x: x[3], reverse=True)[:10]
    for src, dst, rel_type, att_w in sorted_edges:
        src_label = G.nodes[src]["label"]
        dst_label = G.nodes[dst]["label"]
        rel_name = get_relation_name(rel_type)
        print(f"   {src_label} --[{rel_name}]--> {dst_label}  (att={att_w:.6f})", flush=True)


if __name__ == "__main__":
    main()


