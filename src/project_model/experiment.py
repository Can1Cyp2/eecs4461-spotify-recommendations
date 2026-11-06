"""Run the three listening scenarios at five weights and save the results."""
import argparse
from collections import Counter
import csv
from fractions import Fraction
import html
from pathlib import Path

from .domain import SCENARIOS, WEIGHTS, components, load_inputs
from .model import RecommendationModel

ROOT = Path(__file__).resolve().parents[2]
SCENARIO_NAMES = {
    'aligned': 'Aligned',
    'half_different': 'Half different',
    'contrasting': 'Contrasting',
}

def write_csv(path, rows):
    # saves the rows with the column names on the first line:
    with path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path):
    # reads the saved csv rows so the tables and graph use the same results:
    with path.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))


def run_conditions(data_dir):
    # runs each scenario at 0, 0.25, 0.50, 0.75 and 1, keeping 0.50 as the baseline:
    catalogue, profiles, scales = load_inputs(data_dir)
    baseline, alternative = [], []
    for weight in WEIGHTS:
        target = baseline if weight == Fraction(1, 2) else alternative
        for scenario in SCENARIOS:
            model = RecommendationModel(catalogue, profiles, scales, scenario, weight)
            model.run()
            for rank, agent in enumerate(model.ranking(), 1):
                row = {
                    'scenario': scenario, 'weight': float(weight),
                    'candidate_rank': rank, 'track_id': agent.track.track_id,
                    'title': agent.track.title, 'artist': agent.track.artist,
                    'genre': agent.track.genre, 'score': float(agent.score),
                    'score_exact': str(agent.score),
                    'established_similarity': float(agent.established_score),
                    'recent_similarity': float(agent.recent_score),
                    'selected_rank': agent.selected_rank,
                }
                # saves each characteristic match as well as the combined score:
                for label, profile in [('established', model.established), ('recent', model.recent)]:
                    row.update({f'{label}_{key}': float(value)
                                for key, value in components(agent.track, profile, scales).items()})
                target.append(row)
    return baseline, alternative


def playlist_table(out, condition, rows):
    # makes a table of the ten recommended songs for each scenario and weight:
    blocks = []
    for weight in sorted({float(r['weight']) for r in rows}):
        for scenario in SCENARIOS:
            chosen = [r for r in rows if float(r['weight']) == weight
                      and r['scenario'] == scenario and int(r['selected_rank']) > 0]
            chosen.sort(key=lambda r: int(r['selected_rank']))
            counts = Counter(r['genre'] for r in chosen)
            table_rows = []
            for song in chosen:
                cells = [html.escape(str(song[field])) for field in
                         ['selected_rank', 'track_id', 'title', 'artist', 'genre']]
                cells.append(f"{float(song['score']):.6f}")
                table_rows.append('<tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>')
            body = ''.join(table_rows)
            blocks.append(
                f'<section><h2>{SCENARIO_NAMES[scenario]}: w={weight:.2f}</h2>'
                f'<p>Established taste: {1-weight:.0%}. Recent listening: {weight:.0%}.</p>'
                + '<p>Number of recommended songs in each genre: '
                + html.escape(', '.join(f'{genre}: {count}' for genre, count in counts.items()))
                + '</p><div class="table-wrap"><table><thead><tr>'
                + '<th scope="col">Playlist rank</th><th scope="col">Song ID</th>'
                + '<th scope="col">Song</th><th scope="col">Artist</th>'
                + '<th scope="col">Genre</th><th scope="col">Similarity score</th>'
                + '</tr></thead><tbody>' + body + '</tbody></table></div></section>'
            )
    title = 'Baseline recommended playlists' if condition == 'baseline' else 'Alternative recommended playlists'
    explanation = (
        'The baseline uses w=0.50, giving established taste and recent listening equal weight.'
        if condition == 'baseline' else
        'The main alternative uses w=0.75: 25% established taste and 75% recent listening. '
        'The tables also include w=0, 0.25 and 1 from the five weights in my plan.'
    )
    page = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            f'<title>{title}</title>'
            '<style>body{font:16px system-ui;max-width:1100px;margin:32px auto;padding:0 20px}'
            'table{border-collapse:collapse;width:100%}td,th{padding:8px;border-bottom:1px solid #ccc;text-align:left}'
            'h2{margin-top:32px}.table-wrap{overflow-x:auto}table{min-width:720px}'
            'section{margin-bottom:36px}li{margin-bottom:6px}</style></head><body>'
            f'<h1>{title}</h1><p>{explanation}</p>'
            '<p>Each table shows ten songs selected from the 90-song catalogue. Songs used in either '
            'listening set are excluded from recommendations. The listening sets are hypothetical.</p>'
            '<p>The scenarios compare the ten songs in recent listening with the ten in established taste:</p>'
            '<ul><li>Aligned: both sets contain the same ten songs.</li>'
            '<li>Half different: five songs are shared and five are different.</li>'
            '<li>Contrasting: no songs are shared, and genre and tempo differ.</li></ul>'
            '<p>The weight w controls how much recent listening contributes to the score. '
            'It is not the proportion of songs taken from that listening set. '
            'A higher similarity score means a closer match under my scoring rule, '
            'it does not show whether the listener would like the song. '
            'Scores are displayed to six decimal places; ranking uses the exact scores.</p>'
            + ''.join(blocks) + '</body></html>')
    (out / f'{condition}_processed_00_playlists.html').write_text(page, encoding='utf-8')


def compare_weights(rows):
    # compares the recommended song IDs at each weight, separately for each scenario:
    results = []
    weights = [float(w) for w in WEIGHTS]
    for scenario in SCENARIOS:
        ranked = {}
        playlists = {}
        song_sets = {}
        for weight in weights:
            songs = [row for row in rows if row['scenario'] == scenario and float(row['weight']) == weight]
            ranked[weight] = sorted(songs, key=lambda row: int(row['candidate_rank']))
            playlists[weight] = [song['track_id'] for song in ranked[weight][:10]]
            song_sets[weight] = set(playlists[weight])
        # counts each song once across all five playlists, even if it appears more than once:
        different_songs = len(set.union(*song_sets.values()))

        # rank 10 is the last selected song, rank 11 is the first song left out:
        def cutoff_gap(weight):
            return Fraction(ranked[weight][9]['score_exact']) - Fraction(ranked[weight][10]['score_exact'])

        for left, right in zip(weights, weights[1:]):
            previous_songs, next_songs = song_sets[left], song_sets[right]
            # middle weights are 0.25, 0.50 and 0.75; these songs appear at neither 0 nor 1:
            middle_only = next_songs - (song_sets[0.0] | song_sets[1.0]) if right in (.25, .5, .75) else set()
            results.append({
                'scenario': scenario, 'from_weight': left, 'to_weight': right,
                'eligible_count': len(ranked[right]), 'shared': len(previous_songs & next_songs),
                'replacements': 10 - len(previous_songs & next_songs),
                'entered_ids': '|'.join(sorted(next_songs - previous_songs)),
                'left_ids': '|'.join(sorted(previous_songs - next_songs)),
                'same_order': playlists[left] == playlists[right],
                'from_cutoff_gap_exact': str(cutoff_gap(left)), 'to_cutoff_gap_exact': str(cutoff_gap(right)),
                'to_cutoff_gap': float(cutoff_gap(right)),
                'middle_only_ids_at_to_weight': '|'.join(sorted(middle_only)),
                'unique_tracks_all_weights': different_songs, 'additional_tracks_all_weights': different_songs - 10,
            })
    return results


def comparison_plot(out):
    # plots the two comparisons from my plan, with the total different songs shown underneath:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    rows = read_csv(out / 'alternative_processed_01_comparison.csv')
    fig, axes = plt.subplots(1, 2, figsize=(13, 8.5))
    fig.subplots_adjust(left=.07, right=.98, bottom=.43, top=.79, wspace=.28)
    totals = []
    for scenario, color in zip(SCENARIOS, ['#8faab8', '#d49b50', '#386b9d']):
        group = [r for r in rows if r['scenario'] == scenario]
        label = SCENARIO_NAMES[scenario]
        axes[0].plot(range(4), [int(r['replacements']) for r in group], marker='o', color=color, label=label)
        axes[1].plot([.25, .5, .75], [len(r['middle_only_ids_at_to_weight'].split('|'))
                     if r['middle_only_ids_at_to_weight'] else 0 for r in group[:3]], marker='o', color=color)
        totals.append([label, group[0]['unique_tracks_all_weights'], group[0]['additional_tracks_all_weights']])
    axes[0].set_xticks(range(4), ['0 to 0.25', '0.25 to 0.50', '0.50 to 0.75', '0.75 to 1'])
    axes[0].set_xlabel('Change in recent-listening weight (w)', labelpad=9)
    axes[0].set_ylabel('Number of songs replaced (out of 10)')
    axes[0].set_title('Songs replaced when the weight\nincreases by 0.25', pad=14)
    axes[1].set_xticks([.25, .5, .75], ['0.25', '0.50', '0.75'])
    axes[1].set_xlabel('Recent-listening weight (w)', labelpad=9)
    axes[1].set_ylabel('Number of songs (out of 10)')
    axes[1].set_title('Songs recommended only\nat middle weights', pad=14)
    for ax in axes:
        ax.set_ylim(-.15, 10.5)
        ax.set_yticks(range(0, 11, 2))
        ax.spines[['top', 'right']].set_visible(False)
        ax.grid(axis='y', color='#e5e5e5', linewidth=.7)
        ax.set_axisbelow(True)
    fig.suptitle('Recommended songs at different recent-listening weights', fontsize=19, y=.97)
    fig.text(.5, .923, 'w=0 uses only established taste. w=1 uses only recent listening.', ha='center', fontsize=11)
    fig.legend(*axes[0].get_legend_handles_labels(), loc='upper center',
               bbox_to_anchor=(.5, .902), ncol=3, frameon=False)
    fig.text(.07, .338, 'A replacement means a different song enters the ten song playlist.\n'
             'Changing the order of the same songs does not count.', fontsize=10, va='top')
    fig.text(.58, .338, 'These songs are selected at this middle weight,\n'
             'but are not selected at w=0 or w=1.', fontsize=10, va='top')

    # total songs across all weights is a separate measure, so it gets its own table:
    fig.text(.5, .25, 'Different songs recommended across all five weights',
             ha='center', fontsize=13)
    table_axis = fig.add_axes([.12, .09, .76, .135])
    table_axis.axis('off')
    table = table_axis.table(
        cellText=totals,
        colLabels=['Scenario', 'Different songs\nrecommended', 'Additional songs compared with\none ten song playlist'],
        colWidths=[.28, .28, .44], cellLoc='center', bbox=[0, 0, 1, 1],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    for (row, column), cell in table.get_celld().items():
        cell.set_edgecolor('#cccccc')
        if row == 0:
            cell.set_facecolor('#edf1f4')
            cell.set_height(cell.get_height() * 1.5)
    fig.text(.5, .047, 'Weights tested: 0, 0.25, 0.50, 0.75 and 1. Count each song once across the five playlists.',
             ha='center', fontsize=10)
    fig.savefig(out / 'alternative_processed_02_comparison.png', dpi=160)
    plt.close(fig)


def main():
    # runs the model, saves the scores, then makes the tables and graph from those saved scores:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'data')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs')
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    baseline, alternative = run_conditions(args.data_dir)
    write_csv(out / 'baseline_raw_00_rankings.csv', baseline)
    write_csv(out / 'alternative_raw_00_rankings.csv', alternative)
    
    # uses the saved csv files for the playlist tables and comparisons:
    baseline = read_csv(out / 'baseline_raw_00_rankings.csv')
    alternative = read_csv(out / 'alternative_raw_00_rankings.csv')
    playlist_table(out, 'baseline', baseline)
    playlist_table(out, 'alternative', alternative)
    comparisons = compare_weights(baseline + alternative)
    write_csv(out / 'alternative_processed_01_comparison.csv', comparisons)
    comparison_plot(out)
    print('Songs replaced when recent-listening weight changes from 0.50 to 0.75:')
    for row in comparisons:
        if row['from_weight'] == .5 and row['to_weight'] == .75:
            print(f"  {SCENARIO_NAMES[row['scenario']]}: {row['replacements']} of 10 songs replaced")
    print('Different songs recommended across all five weights (each song counted once):')
    for scenario in SCENARIOS:
        row = next(row for row in comparisons if row['scenario'] == scenario)
        print(f"  {SCENARIO_NAMES[scenario]}: {row['unique_tracks_all_weights']} songs")
    print(f'Saved six output files in {out}')


if __name__ == '__main__':
    main()
