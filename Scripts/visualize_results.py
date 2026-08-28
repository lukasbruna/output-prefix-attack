import os
import json
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from matplotlib.lines import Line2D
import numpy as np
import seaborn as sns

# Set global academic style
plt.rcParams.update({
    'font.size': 14,
    'axes.titlesize': 18,
    'axes.labelsize': 16,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 14,
    'figure.titlesize': 20,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'savefig.dpi': 300
})

LABEL_MAP = {1: 'Hit', 2: 'Partial Hit', 3: 'Miss'}
MODE_DISPLAY_MAP = {
    'baseline': 'baseline',
    'fixed': 'static prefix',
    'dataset': 'dataset pair',
    'json_only': 'reasoning only',
    'json_prefix': 'reasoning static prefix',
    'json_dataset': 'reasoning dataset pair'
}
MODE_ORDER = ['baseline', 'static prefix', 'dataset pair', 'reasoning only', 'reasoning static prefix', 'reasoning dataset pair']
MODEL_LABEL_MAP = {
    "claude-haiku-4-5": "Claude Haiku 4.5",
    "deepseek-v4-flash": "DeepSeek V4 Flash",
    "gemini-3-flash-preview": "Gemini 3 Flash Preview",
}

def load_data(input_dir):
    all_data = []
    for filepath in Path(input_dir).rglob('*.json*'):
        with open(filepath, 'r') as f:
            for line in f:
                try:
                    all_data.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return pd.DataFrame(all_data)

def get_ordered_modes(df):
    existing_modes = df['mode'].unique()
    return [m for m in MODE_ORDER if m in existing_modes]

def plot_heatmap_hit_rate(df, output_dir, palette):
    df['is_hit'] = (df['rating'] == 1).astype(int)
    pivot = df.pivot_table(index='model', columns='mode', values='is_hit', aggfunc='mean')
    ordered_modes = get_ordered_modes(df)
    pivot = pivot[ordered_modes]

    plt.figure(figsize=(12, 8))

    pretty_index = [MODEL_LABEL_MAP.get(m, m) for m in pivot.index]
    pivot.index = pretty_index

    sns.heatmap(pivot, annot=True, fmt=".2f", cmap=palette,
                annot_kws={"size": 20, "weight": "bold"},
                cbar_kws={'label': 'Hit Rate'})

    plt.xticks(rotation=45, ha='right', fontsize=16, fontweight='bold')
    plt.yticks(rotation=45, fontsize=16, fontweight='bold')
    plt.xlabel('Mode', fontsize=16, fontweight='bold')
    plt.ylabel('Model', fontsize=16, fontweight='bold')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'hit_rate_heatmap.png'))
    plt.close()

def plot_model_mode_stacked_bars(df, output_dir, palette):
    models = sorted(df['model'].unique())
    modes = get_ordered_modes(df)

    # Generate 3 colors from the palette
    colors = sns.color_palette(palette, 3)
    color_map = {1: colors[0], 2: colors[1], 3: colors[2]}

    fig, ax = plt.subplots(figsize=(20, 15))
    num_models, num_modes = len(models), len(modes)
    total_group_width = 0.9
    bar_width = (total_group_width / num_modes) * 0.9

    all_tick_positions, all_tick_labels = [], []
    for i, model in enumerate(models):
        for j, mode in enumerate(modes):
            pos = i - (total_group_width/2) + (j + 0.5) * (total_group_width/num_modes)
            all_tick_positions.append(pos)
            all_tick_labels.append(str(j + 1))
            subset_all = df[(df['model'] == model) & (df['mode'] == mode)]
            total, bottom = len(subset_all), 0
            for rating in [1, 2, 3]:
                pct = (len(subset_all[subset_all['rating'] == rating]) / total * 100) if total > 0 else 0
                ax.bar(pos, pct, bar_width, bottom=bottom, color=color_map[rating])
                bottom += pct

    ax.tick_params(axis='y', labelsize=36)
    ax.set_xticks(all_tick_positions)
    ax.set_xticklabels(all_tick_labels, fontsize=30, fontweight='bold')

    for i, model in enumerate(models):
        pretty_name = MODEL_LABEL_MAP.get(model, model)
        ax.text(i, -10, pretty_name, ha='center', va='top', fontsize=30, fontweight='bold')

    ax.set_ylabel('Percentage (%)', fontsize=36, fontweight='bold')
    ax.set_ylim(0, 100)
    custom_lines = [Line2D([0], [0], color=color_map[r], lw=6) for r in [3, 2, 1]]
    ax.legend(custom_lines, [LABEL_MAP[r] for r in [3, 2, 1]], title='Test Evaluation', title_fontsize=30, fontsize=30)
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.25)
    plt.savefig(os.path.join(output_dir, 'model_mode_stacked_bars.png'))
    plt.close()

def main():
    parser = argparse.ArgumentParser(description="Visualize LLM safety evaluation results.")
    parser.add_argument("--input_dir", default="Results/Evaluation", help="Directory containing evaluation result files.")
    parser.add_argument("--output_dir", default="Graphs", help="Directory where generated plots will be saved.")
    parser.add_argument("--palette", default="viridis", help="Seaborn color palette to use.")
    args = parser.parse_args()

    df = load_data(args.input_dir)
    if df.empty:
        print(f"No data found in '{args.input_dir}'.")
        return

    if 'mode' in df.columns:
        df['mode'] = df['mode'].replace(MODE_DISPLAY_MAP)
    if 'model' in df.columns:
        df['model'] = df['model'].replace('claude-haiku-4-5-20251001', 'claude-haiku-4-5')

    os.makedirs(args.output_dir, exist_ok=True)
    print(f"Generating 2 graphs from {len(df)} records using palette '{args.palette}'...")
    plot_heatmap_hit_rate(df, args.output_dir, args.palette)
    plot_model_mode_stacked_bars(df, args.output_dir, args.palette)
    print(f"Graphs generated in '{args.output_dir}/'.")

if __name__ == "__main__":
    main()
