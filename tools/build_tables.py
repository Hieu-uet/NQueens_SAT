"""Generate the paper's TeX tables from validated analysis.json (standard library)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
analysis = json.loads((ROOT / 'data/analysis.json').read_text(encoding='utf-8'))
groups = {(g['n'], g['method']): g for g in analysis['summary']}
METHODS = ['pairwise', 'seqcounter', 'bitwise', 'cp_sat', 'gurobi_mip', 'cplex_mip', 'cplex_cp']
NAMES = ['SAT pairwise', 'SAT seqcounter', 'SAT bitwise', 'CP-SAT', 'Gurobi MIP', 'CPLEX MIP', 'CP Optimizer']
SIZES = [8, 16, 24, 31, 32, 64, 128]

def integer(v):
    return format(v, ',').replace(',', r'\,')

def number(v):
    return format(v, ',.3f').replace(',', r'\,')

def row(values):
    return ' & '.join(map(str, values)) + r' \\' + '\n'

def save(name, caption, label, columns, header, rows, note='', size=r'\small'):
    tex = ('\\begin{table}[htbp]\n\\caption{' + caption + '}\\label{' + label + '}\n'
           + '\\centering' + size + '\n\\begin{tabular}{' + columns + '}\n\\toprule\n'
           + row(header) + '\\midrule\n' + ''.join(row(r) for r in rows)
           + '\\bottomrule\n\\end{tabular}\n')
    if note:
        tex += '\\tabnote{' + note + '}\n'
    tex += '\\end{table}\n'
    (ROOT / 'tables' / name).write_text(tex, encoding='utf-8')

status = []
for method, name in zip(METHODS, NAMES):
    selected = [groups[n, method] for n in SIZES]
    sums = {k: sum(g[k] for g in selected) for k in ('attempted', 'sat', 'solve_timeout', 'license_limit')}
    status.append([name, sums['attempted'], sums['sat'], sums['solve_timeout'], sums['license_limit'],
                   f"{sums['sat']}/{sums['attempted']}"])
status.append([r'\textbf{Tổng}', 220, 210, 10, 25, '210/220'])
save('status.tex', 'Trạng thái 245 lượt theo lịch; warm-up được ghi riêng.', 'tab:status', 'lrrrrc',
     ['Phương pháp', 'Đã gọi', 'SAT', 'TO', 'GL', 'SAT/đã gọi'], status)

total = []
for method, name in zip(METHODS, NAMES):
    values = [name]
    for n in SIZES:
        g = groups[n, method]
        values.append(r'\GL' if g['license_limit'] else r'\TO' if g['solve_timeout'] else number(g['total_s_median'] * 1000))
    total.append(values)
save('total.tex', 'Trung vị tổng thời gian của năm lượt, đơn vị ms.', 'tab:total', 'lrrrrrrr',
     ['Phương pháp'] + [f'$N={n}$' for n in SIZES], total,
     r'Dùng dấu chấm cho phần thập phân và khoảng mảnh để nhóm hàng nghìn. \TO: hết hạn giải 5/5 lượt. \GL: bỏ qua 5/5 lượt theo giấy phép, không đo thời gian.', size=r'\footnotesize\setlength{\tabcolsep}{4pt}')

cnf = []
for n in SIZES:
    values = [n]
    for method in METHODS[:3]:
        g = groups[n, method]
        values.extend([integer(g['model_vars']), integer(g['cnf_clauses'])])
    cnf.append(values)
save('cnf.tex', 'Số biến xuất hiện trong CNF (V) và số mệnh đề được dựng (C).', 'tab:cnf', 'rrrrrrr',
     ['$N$', 'Pairwise V', 'Pairwise C', 'Seqcounter V', 'Seqcounter C', 'Bitwise V', 'Bitwise C'], cnf,
     'V bao gồm biến gốc và biến phụ. Các số đếm của cùng một cấu hình không đổi qua năm lượt.', size=r'\footnotesize\setlength{\tabcolsep}{5pt}')

phase = []
wall = []
for method, name in zip(METHODS, NAMES):
    g = groups[128, method]
    if g['sat'] == 5:
        phase.append([name] + [number(g[f'{k}_s_median'] * 1000) for k in ('build','init','solve','post','total')])
        wall.append([name, number(g['total_s_median'] * 1000), number(g['process_wall_s_median'] * 1000)])
save('phases.tex', 'Trung vị từng pha tại $N=128$, đơn vị ms; chỉ các cấu hình có 5/5 SAT.', 'tab:phases', 'lrrrrr',
     ['Phương pháp', 'Dựng', 'Khởi tạo', 'Giải', 'Hậu xử lý', 'Tổng'], phase,
     'Trung vị từng cột được tính độc lập; tổng các trung vị thành phần không nhất thiết bằng trung vị tổng.')
save('wall.tex', 'Hai phạm vi đo khác nhau tại $N=128$, trung vị năm lượt (ms).', 'tab:wall', 'lrr',
     ['Phương pháp', '$t_{\\mathrm{total}}$', r'\code{process_wall_s}'], wall,
     'Cột cuối bao gồm khởi động tiến trình, import, thống kê, giao tiếp và thu hồi; đã đổi từ giây sang ms.')
print('Generated 5 tables from', ROOT / 'data/analysis.json')
