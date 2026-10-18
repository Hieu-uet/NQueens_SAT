# Báo cáo N-Queens bằng SAT

Bản thảo đầy đủ theo `\documentclass[a4paper,fleqn]{cas-sc}`, viết bằng tiếng Việt, dùng số liệu thí nghiệm chính ngày 16/10/2026. Tác giả: Đặng Trung Hiếu.

## Mở và sửa trên Overleaf

1. Tạo dự án bằng **New Project → Upload Project**, chọn ZIP này.
2. Chọn tệp chính **main.tex**, compiler **XeLaTeX**.
3. Bấm **Recompile**. Các tệp lớp CAS và font đã được kèm trong gói.
4. Chỉnh tên/đơn vị nếu cần trong `config.tex`.
5. Điền URL thật vào `\CodeURL` và `\DataURL` trong `config.tex`. Khi điền, hai nhãn “Chưa bổ sung” sẽ tự thay thành liên kết.
6. Sau khi kiểm tra các URL truy cập được, sửa/xóa câu ghi chú bản thảo ở `\nonumnote` và đoạn thông báo chưa có URL trong mục Data Availability của `main.tex`. Có thể đổi dòng chân trang từ “Bản thảo” sang “Bản nộp” khi thực sự hoàn tất.

## Biên dịch cục bộ

Cần TeX Live hoặc MiKTeX có XeLaTeX và các gói LaTeX thông dụng. Chạy từ thư mục chứa `main.tex`:

```text
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
```

Nếu không có latexmk:

```text
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

## Thành phần

- `main.tex`: toàn bộ bài báo; `config.tex`: thông tin và hai URL cần bổ sung.
- `references.bib`: 10 tài liệu tham khảo gốc; `tables/`: bảng tự sinh từ số liệu.
- `figures/`: ba biểu đồ vector PDF, không mất nét khi phóng to.
- `data/main_v1_20261016_224847_037042.zip`: nguyên tệp dữ liệu gốc gồm measurements, warmup và manifest.
- `data/analysis.json`, `data/summary.csv`: kết quả kiểm tra và 49 nhóm thống kê. Thời gian trong các tệp dữ liệu là **giây**, trong bảng bài báo là **ms**.
- `tools/analyze_results.py`: phân tích lại dữ liệu bằng Python chuẩn, không cần cài solver.
- `tools/build_tables.py`: sinh lại năm bảng TeX từ `data/analysis.json`.
- `cas-sc.cls`, `cas-common.sty`, `cas-model2-names.bst`: tệp CAS chính thức, giữ nguyên nội dung.
- `template_original/`: hướng dẫn, manifest và template nguyên gốc của gói CAS 2.4.
- `fonts/`: DejaVu Serif/Sans và thông tin bản quyền.

## Tái kiểm tra số liệu mà không chạy lại solver

```text
python tools/analyze_results.py data/main_v1_20261016_224847_037042.zip --output analysis_recheck
python tools/build_tables.py
```

Lệnh đầu tạo kết quả đối chiếu riêng. Lệnh sau dùng **data/analysis.json** đang đóng gói, không tự lấy tệp trong analysis_recheck.

## Việc còn lại trước khi nộp

1. Bổ sung kho mã nguồn thật và URL dữ liệu thô. Kho mã phải chứa các mô-đun thực tế đã chạy ở máy Windows; manifest đã ghi SHA-256 để đối chiếu.
2. Kiểm tra thông tin tác giả và những thông tin riêng giảng viên yêu cầu (MSSV/lớp nếu cần). Không có MSSV hoặc email được tự tạo trong bản thảo.
3. Đọc lại các đoạn giải thích và chuẩn bị trình bày các khái niệm: biến phụ, ba AMO, kiểm tra nghiệm, phạm vi thời gian và giới hạn giấy phép.
4. Không đổi GL thành timeout/UNSAT, không gán giá trị thời gian giả cho các ô thiếu dữ liệu.

Gói này là **mã nguồn báo cáo và dữ liệu**, không phải toàn bộ dự án solver. Dữ liệu nguồn là thí nghiệm chính; không trộn các đợt pilot hoặc dữ liệu kiểm thử.

## Ghi nhận nguồn template và font

CAS 2.4 (04/05/2024), Elsevier, lấy từ CTAN:
https://ctan.org/tex-archive/macros/latex/contrib/els-cas-templates

Các tệp lớp gốc được phân phối theo LaTeX Project Public License; xem đầu tệp và `template_original/README`. Tùy biến tiếng Việt, giấy A4 và chân trang chỉ nằm trong `main.tex`; không sửa lớp gốc. Font được phân phối kèm giấy phép ở `fonts/LICENSE.txt`.

Hai kiểu chữ nghiêng trong bài dùng biến đổi nghiêng từ font DejaVu đi kèm để gói có thể biên dịch độc lập. Các số liệu và biểu đồ do phân tích dữ liệu gốc tạo ra; không phải dữ liệu minh họa.
