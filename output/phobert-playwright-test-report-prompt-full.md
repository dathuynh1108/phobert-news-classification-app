# Prompt cho Prism - cập nhật test report vào LaTeX

Bạn hãy cập nhật báo cáo LaTeX "Hệ thống phân loại và kiểm duyệt tin tức tiếng Việt sử dụng PhoBERT" dựa trên dữ liệu kiểm thử dưới đây. Viết bằng tiếng Việt học thuật, rõ ràng, không phóng đại kết quả. Phần này dùng để ghép vào chương kiểm thử/demo, không thay thế toàn bộ report.

## Quy tắc bắt buộc

1. Chỉ dùng một bộ ảnh: `test-report-assets-full/`.
2. Chỉ dùng các ảnh được liệt kê trong mục `Danh sách hình cần chèn`. Không tự kéo thêm ảnh hoặc JSON log ngoài danh sách đó vào report.
3. Không claim dữ liệu fake/mock. Bộ dữ liệu hiện tại là bài VietnamNet thật, đã import/infer qua model-service thật.
4. Không claim "đã pass" cho use case chỉ mới thấy nút/form nhưng chưa thực sự submit/click. Với các case đó ghi là "đã kiểm tra giao diện/khả năng hiển thị", hoặc "chưa thực thi trong lượt test này".
5. Không tạo use case riêng cho ảnh source VietnamNet. Ảnh source chỉ là bằng chứng nguồn dữ liệu test, không phải chức năng của app.
6. Nếu report có bảng use case hiện tại UC01-UC28, thay toàn bộ bảng đó bằng danh sách use case mới trong prompt này để khớp với hệ thống hiện tại.
7. Không nhắc bài demo cũ hoặc article id cũ; toàn bộ nội dung phải bám theo dữ liệu VietnamNet thật được liệt kê trong prompt này.

## Vị trí cần sửa trong report

1. Trong mục `5.3 Kế hoạch kiểm thử`, bổ sung tiểu mục `5.3.1 Test report chức năng`.
2. Thêm tiểu mục `5.3.2 Đối chiếu use case và bằng chứng kiểm thử`.
3. Thêm tiểu mục ngắn `5.3.3 Bộ dữ liệu kiểm thử và ảnh nguồn bài báo` nếu report cần giải thích vì sao dữ liệu không phải input tự chế.
4. Cập nhật `Danh sách hình vẽ` với caption ngắn dạng `Hình 5.x`.
5. Trong kết luận, thêm một câu rằng hệ thống đã được kiểm thử qua UI với API-service, model-service, Postgres/Redis và artifact PhoBERT active; đồng thời nêu các case chưa chạy đầy đủ là hướng kiểm thử bổ sung.

## Danh sách use case đề xuất thay thế

Hãy thay bảng use case cũ trong report bằng danh sách dưới đây. Không dựa vào bảng UC cũ nữa. Danh sách này chỉ giữ mã UC01-UC28 cho dễ tham chiếu, còn nội dung được viết lại theo chức năng thật có trong UI/app hiện tại:

- `Editor`: thao tác biên tập, import bài, review prediction, quyết định nhãn.
- `Admin`: quản trị user, threshold, audit và promote model từ Admin Ops.
- `Data Scientist`: monitoring, model versions, artifact, dataset lab.
- `System operator`: kiểm tra health/runtime.

Không thêm use case riêng cho ảnh nguồn VietnamNet. Các endpoint job không có màn hình độc lập trong UI, nên chỉ mô tả chúng như cơ chế nội bộ của import và monitoring recompute.

Thay bảng use case bằng đoạn LaTeX sau:

```latex
UC01 & All roles & Đăng nhập theo vai trò & Xác thực email, mật khẩu và role; nhận Bearer token, thông tin user, active model và redirect đúng workspace. \\
UC02 & All roles & Đăng xuất & Gọi API logout, hủy session phía client và quay về màn hình đăng nhập. \\
UC03 & Editor & Xem Editor dashboard & Xem active model, thống kê nhanh, form import, editorial queue, category distribution và menu đúng quyền Editor. \\
UC04 & Editor & Nhập nguồn bài báo & Nhập source URL hoặc nhập thủ công title, content, source để chuẩn bị đưa bài vào pipeline. \\
UC05 & Editor & Import bài bất đồng bộ & Tạo worker job article_import qua Redis/Dramatiq, crawl nội dung từ URL khi cần, lưu article/prediction vào Postgres và poll trạng thái job. \\
UC06 & Editor & Theo dõi kết quả import & UI poll trạng thái worker job và refresh dashboard khi article/prediction đã được lưu. \\
UC07 & Editor & Xem Review Queue & Xem danh sách bài có status review hoặc escalated, kèm label dự đoán, confidence, margin, status và phân trang. \\
UC08 & Editor & Xem Article Detail & Xem nội dung bài, source URL, prediction summary, candidate ranking, threshold bands, rationale, bài tương tự và lịch sử xử lý. \\
UC09 & Editor & Chạy inference cho bài hiện có & Gửi title, content và source URL của bài đã lưu đến PhoBERT model-service; lưu label, confidence, margin, candidates và auto-decision. \\
UC10 & Editor & Refresh URL rồi inference & Cập nhật source URL của bài, crawl lại nội dung từ URL, làm sạch text và chạy phân loại lại qua model-service. \\
UC11 & Editor & Approve prediction & Chấp nhận nhãn model dự đoán và lưu decision approved. \\
UC12 & Editor & Override label & Chọn nhãn khác với prediction, lưu selected label và notes cho feedback loop. \\
UC13 & Editor & Escalate bài báo & Đẩy bài có confidence thấp hoặc cần xem xét thêm sang trạng thái escalated/Data Science. \\
UC14 & Editor & Xem Label Review & Xem danh sách bài đã có nhãn/prediction để kiểm tra chất lượng nhãn, confidence, margin và trạng thái quyết định. \\
UC15 & Admin & Xem Admin Operations & Xem users, permissions, routing thresholds, threshold impact, audit log và deployment snapshot. \\
UC16 & Admin & Tạo user & Tạo user mới với email, tên, role, queue và mật khẩu ban đầu. \\
UC17 & Admin & Cập nhật user & Sửa tên, role, queue, trạng thái hoặc mật khẩu của user hiện có. \\
UC18 & Admin & Cập nhật threshold & Lưu auto-approve threshold và review floor dùng cho routing auto-approved/review/escalated. \\
UC19 & Admin & Preview threshold impact & Tính thử tác động của threshold mới lên phân phối auto-ready, manual review và escalated mà chưa lưu rule. \\
UC20 & Admin & Promote model từ Admin Ops & Kích hoạt candidate model run từ trang Admin Operations để thay active package phục vụ inference. \\
UC21 & Data Scientist & Xem Monitoring dashboard & Xem evaluation snapshot, macro F1, error share, drift score, coverage, per-label F1, confusion matrix, slice analysis và per-class metrics. \\
UC22 & Data Scientist & Recompute monitoring qua worker & Enqueue monitoring_recompute job qua Redis/Dramatiq, poll job đến completed và đọc snapshot mới trên dashboard. \\
UC23 & Data Scientist & Xem Model Versions & Xem uploaded runs, active run, backbone, F1, package details, confusion matrix, required package files và exports. \\
UC24 & Data Scientist & Upload artifact & Upload một file zip hoặc tập artifact files cho model run; kiểm tra đủ config, label_config, checkpoint và tokenizer files. \\
UC25 & Data Scientist & Activate artifact & Set một model run làm active package từ trang Model Versions. \\
UC26 & Data Scientist & Download export & Tải các file export của selected model run để kiểm tra hoặc triển khai. \\
UC27 & Data Scientist & Dataset Lab & Xem stored articles, low-confidence pool, label imbalance, hard samples, active-learning loop và priority labels. \\
UC28 & System operator & Health check runtime & Kiểm tra API health, Postgres và model-service; xác nhận Redis/worker qua các worker job và Docker Compose runtime. \\
```

## Đặc tả use case chi tiết cần thêm vào LaTeX

Hãy thêm hoặc thay thế section đặc tả use case trong report bằng block dưới đây. Giữ đúng cấu trúc `longtable`, không rút gọn còn "use case tiêu biểu" vì report cần đặc tả đầy đủ cho UC01-UC28. Các use case bên dưới chỉ mô tả chức năng thật có trong UI/app hiện tại; job API không đứng riêng làm use case.

```latex
\section{Đặc tả use case}

\subsection[UC-AUTH-LOGIN]{UC01 - Đăng nhập theo vai trò}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor, Admin, Data Scientist. \\
Tiền điều kiện & Người dùng có tài khoản hợp lệ và chọn đúng vai trò được cấp. \\
Hậu điều kiện & Session token được tạo; UI lưu token và điều hướng về workspace tương ứng. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Người dùng nhập email, mật khẩu và chọn role.
    \item UI gửi \texttt{POST /auth/login}.
    \item API kiểm tra email, mật khẩu và role.
    \item API trả Bearer token, thông tin user, active model và redirect path.
    \item UI lưu session và hiển thị sidebar theo role.
\end{enumerate} \\
Luồng thay thế & Nếu sai email, mật khẩu hoặc role, API trả 401. Nếu truy cập route ngoài quyền, UI redirect về workspace hợp lệ của role hiện tại. \\
\bottomrule
\end{longtable}

\subsection[UC-AUTH-LOGOUT]{UC02 - Đăng xuất}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor, Admin, Data Scientist. \\
Tiền điều kiện & Người dùng đã đăng nhập và có session token trong trình duyệt. \\
Hậu điều kiện & Session phía client bị xóa; người dùng quay về màn hình đăng nhập. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Người dùng mở account menu.
    \item Người dùng chọn Sign out.
    \item UI gửi \texttt{POST /auth/logout} kèm Bearer token.
    \item UI xóa session khỏi local storage.
    \item UI điều hướng về trang login.
\end{enumerate} \\
Luồng thay thế & Nếu request logout lỗi mạng, UI vẫn xóa session local để người dùng không tiếp tục thao tác bằng session cũ. \\
\bottomrule
\end{longtable}

\subsection[UC-EDITOR-DASHBOARD]{UC03 - Xem Editor dashboard}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Editor đã đăng nhập. \\
Hậu điều kiện & Dashboard hiển thị active model, thống kê nhanh và các panel phục vụ review. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor truy cập route dashboard.
    \item UI gửi \texttt{GET /editor/dashboard}.
    \item API kiểm tra role Editor.
    \item API tổng hợp stats, review queue, category distribution và shared signals.
    \item UI hiển thị dashboard và sidebar đúng quyền.
\end{enumerate} \\
Luồng thay thế & Nếu token không hợp lệ, API trả 401. Nếu role không phải Editor, API trả 403 hoặc UI redirect về workspace phù hợp. \\
\bottomrule
\end{longtable}

\subsection[UC-ARTICLE-INPUT]{UC04 - Nhập nguồn bài báo}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Editor đã đăng nhập. \\
Hậu điều kiện & UI có payload gồm source URL hoặc title/content/source để gửi vào pipeline import. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor mở form Import article.
    \item Editor nhập source URL hoặc nhập thủ công title, content và source.
    \item UI giữ dữ liệu form ở trạng thái chờ submit.
    \item Editor bấm Queue import để chuyển bài vào pipeline.
\end{enumerate} \\
Luồng thay thế & Nếu thiếu cả URL lẫn title/content, UI không gửi request import. Nếu URL không lấy được nội dung, API yêu cầu bổ sung dữ liệu hợp lệ. \\
\bottomrule
\end{longtable}

\subsection[UC-ARTICLE-IMPORT-ASYNC]{UC05 - Import bài bất đồng bộ}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor, worker-service. \\
Tiền điều kiện & Editor đã đăng nhập; Redis và worker-service hoạt động; model-service sẵn sàng nếu import có inference. \\
Hậu điều kiện & Worker job \texttt{article\_import} hoàn tất; article và prediction được lưu vào Postgres. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor bấm Queue import.
    \item UI gửi \texttt{POST /editor/articles/jobs}.
    \item API tạo worker job và enqueue vào Redis.
    \item Worker crawl/làm sạch nội dung nếu payload có URL.
    \item Worker gọi model-service khi \texttt{run\_inference=true}.
    \item Worker lưu article, prediction, status và job result.
\end{enumerate} \\
Luồng thay thế & Nếu enqueue thất bại, API đánh dấu job failed và trả 503. Nếu dữ liệu thiếu, API trả 422. Nếu model-service lỗi, job hoặc request bị failed. \\
\bottomrule
\end{longtable}

\subsection[UC-IMPORT-JOB-STATUS]{UC06 - Theo dõi kết quả import}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Editor đã enqueue import job từ dashboard. \\
Hậu điều kiện & UI hiển thị trạng thái job; dashboard được refresh khi article/prediction đã lưu. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item UI nhận \texttt{job\_id} từ API sau khi queue import.
    \item UI hiển thị trạng thái đang chờ worker.
    \item UI poll \texttt{GET /jobs/\{job\_id\}}.
    \item Khi job completed, UI gọi lại \texttt{GET /editor/dashboard}.
    \item UI hiển thị bài mới trong queue hoặc stats tương ứng.
\end{enumerate} \\
Luồng thay thế & Nếu job failed, UI hiển thị lỗi từ job. Nếu job chạy quá lâu, UI dừng polling và báo import vẫn đang chạy. \\
\bottomrule
\end{longtable}

\subsection[UC-REVIEW-QUEUE]{UC07 - Xem Review Queue}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Editor đã đăng nhập; hệ thống có bài status review hoặc escalated. \\
Hậu điều kiện & Editor thấy danh sách bài cần kiểm duyệt và có thể mở Article Detail. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor mở Review Queue.
    \item UI gửi \texttt{GET /editor/review}.
    \item API trả danh sách bài review/escalated, stats và phân trang.
    \item UI hiển thị label, confidence, margin, status và nút Open.
\end{enumerate} \\
Luồng thay thế & Nếu không có bài cần review, UI hiển thị empty state. Nếu token không hợp lệ, API trả 401. \\
\bottomrule
\end{longtable}

\subsection[UC-ARTICLE-DETAIL]{UC08 - Xem Article Detail}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Article tồn tại và Editor có quyền truy cập. \\
Hậu điều kiện & Editor có đủ thông tin để approve, override hoặc escalate. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor mở một bài từ Review Queue hoặc Label Review.
    \item UI gửi \texttt{GET /editor/articles/\{article\_id\}}.
    \item API trả article content, source URL, prediction summary, candidates và decision controls.
    \item UI hiển thị article body, rationale, similar stories, threshold bands và history.
\end{enumerate} \\
Luồng thay thế & Nếu article không tồn tại, API trả 404. Nếu role không phải Editor, API trả 403. \\
\bottomrule
\end{longtable}

\subsection[UC-ARTICLE-INFER]{UC09 - Chạy inference cho bài hiện có}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Article đã tồn tại; model-service có artifact active hợp lệ. \\
Hậu điều kiện & Prediction mới được lưu gồm label, confidence, margin, candidates, latency và auto-decision. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor mở Article Detail.
    \item Editor nhấn Run inference.
    \item UI gửi \texttt{POST /editor/articles/\{article\_id\}/infer}.
    \item API gọi gRPC classifier với title, content và source URL.
    \item API lưu prediction và cập nhật status của article.
\end{enumerate} \\
Luồng thay thế & Nếu article không tồn tại, API trả 404. Nếu model-service không sẵn sàng, request trả lỗi service. \\
\bottomrule
\end{longtable}

\subsection[UC-ARTICLE-REFRESH-INFER]{UC10 - Refresh URL rồi inference}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Article tồn tại; Editor nhập URL mới hoặc URL cần crawl lại; model-service sẵn sàng. \\
Hậu điều kiện & Nội dung article và prediction được cập nhật theo URL mới. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor chỉnh Source URL trong Article Detail.
    \item Editor nhấn Run inference.
    \item UI gửi \texttt{POST /editor/articles/\{article\_id\}/infer-url}.
    \item API fetch nội dung từ URL và làm sạch title/content.
    \item API gọi model-service và lưu prediction mới.
\end{enumerate} \\
Luồng thay thế & Nếu URL không cung cấp title hoặc content hợp lệ, API trả 422. Nếu article không tồn tại, API trả 404. \\
\bottomrule
\end{longtable}

\subsection[UC-DECISION-APPROVE]{UC11 - Approve prediction}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Article tồn tại và có prediction để duyệt. \\
Hậu điều kiện & Prediction được chấp nhận; article status/selected label được lưu phục vụ feedback loop. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor mở Article Detail.
    \item Editor kiểm tra content, prediction và candidates.
    \item Editor bấm Approve label.
    \item UI gửi \texttt{POST /editor/articles/\{article\_id\}/decision} với action approve.
    \item API lưu decision approved và trả status.
\end{enumerate} \\
Luồng thay thế & Nếu article không tồn tại, API trả 404. Nếu action không hợp lệ, API trả 422. \\
\bottomrule
\end{longtable}

\subsection[UC-DECISION-OVERRIDE]{UC12 - Override label}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Article tồn tại; Editor xác định prediction cần sửa sang nhãn khác. \\
Hậu điều kiện & Selected label mới và notes được lưu; record trở thành feedback cho monitoring/dataset lab. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor mở Article Detail.
    \item Editor chọn nhãn mới trong label select.
    \item Editor nhập notes nếu cần.
    \item UI gửi decision với action override và selected label.
    \item API validate nhãn, lưu override và cập nhật article.
\end{enumerate} \\
Luồng thay thế & Nếu selected label thiếu hoặc không hợp lệ, API trả 422. Nếu article không tồn tại, API trả 404. \\
\bottomrule
\end{longtable}

\subsection[UC-DECISION-ESCALATE]{UC13 - Escalate bài báo}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Article tồn tại; bài cần Data Scientist hoặc review sâu hơn. \\
Hậu điều kiện & Article được đưa sang trạng thái escalated và xuất hiện trong các slice monitoring liên quan. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor mở Article Detail.
    \item Editor đọc prediction, confidence và candidates.
    \item Editor bấm Escalate hoặc Flag to DS.
    \item UI gửi decision với action escalate.
    \item API lưu trạng thái escalated và trả status.
\end{enumerate} \\
Luồng thay thế & Nếu article không tồn tại, API trả 404. Nếu action không hợp lệ, API trả 422. \\
\bottomrule
\end{longtable}

\subsection[UC-LABEL-REVIEW]{UC14 - Xem Label Review}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Editor. \\
Tiền điều kiện & Editor đã đăng nhập; hệ thống có bài đã có prediction hoặc decision. \\
Hậu điều kiện & Editor theo dõi được chất lượng nhãn, confidence, margin và trạng thái xử lý. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Editor mở Label Review.
    \item UI gửi \texttt{GET /editor/classifier}.
    \item API trả classified stories, stats và phân trang.
    \item UI hiển thị label, article title, confidence, margin, status và link Inspect.
\end{enumerate} \\
Luồng thay thế & Nếu chưa có bài classified, UI hiển thị empty state. Nếu token không hợp lệ, API trả 401. \\
\bottomrule
\end{longtable}

\subsection[UC-ADMIN-OPS]{UC15 - Xem Admin Operations}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Admin. \\
Tiền điều kiện & Admin đã đăng nhập. \\
Hậu điều kiện & Admin thấy users, audit log, thresholds, threshold impact và deployment snapshot. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Admin mở Admin Ops.
    \item UI gửi \texttt{GET /admin/ops}.
    \item API kiểm tra role Admin.
    \item API trả users, audit log, thresholds, threshold impact và deployment snapshot.
    \item UI hiển thị các panel quản trị.
\end{enumerate} \\
Luồng thay thế & Nếu role không phải Admin, API trả 403. Nếu token không hợp lệ, API trả 401. \\
\bottomrule
\end{longtable}

\subsection[UC-ADMIN-CREATE-USER]{UC16 - Tạo user}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Admin. \\
Tiền điều kiện & Admin đã đăng nhập; email user mới chưa bị trùng. \\
Hậu điều kiện & User mới được lưu với role, queue, status và password ban đầu. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Admin mở form Create user.
    \item Admin nhập email, name, role, queue và temporary password.
    \item UI gửi \texttt{POST /admin/users}.
    \item API validate payload và role.
    \item API tạo user, ghi audit và trả user mới.
\end{enumerate} \\
Luồng thay thế & Nếu thiếu email/password hoặc role không hợp lệ, API trả lỗi validate. Nếu email đã tồn tại, API trả lỗi tương ứng. \\
\bottomrule
\end{longtable}

\subsection[UC-ADMIN-UPDATE-USER]{UC17 - Cập nhật user}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Admin. \\
Tiền điều kiện & Admin đã đăng nhập; user cần sửa tồn tại. \\
Hậu điều kiện & Thông tin user được cập nhật và audit log ghi nhận thay đổi. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Admin bấm Edit ở một dòng user.
    \item Admin sửa name, role, queue, status hoặc password.
    \item UI gửi \texttt{PATCH /admin/users/\{email\}}.
    \item API validate payload.
    \item API cập nhật user và trả dữ liệu mới.
\end{enumerate} \\
Luồng thay thế & Nếu user không tồn tại, API trả 404. Nếu role hoặc status không hợp lệ, API trả lỗi validate. \\
\bottomrule
\end{longtable}

\subsection[UC-THRESHOLD-UPDATE]{UC18 - Cập nhật threshold}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Admin. \\
Tiền điều kiện & Admin đã đăng nhập; threshold mới nằm trong khoảng hợp lệ. \\
Hậu điều kiện & Auto-approve threshold và review floor mới được lưu, ảnh hưởng đến routing inference tiếp theo. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Admin chỉnh slider Auto-approve và Review floor.
    \item Admin bấm Update rules.
    \item UI gửi \texttt{POST /admin/ops/thresholds}.
    \item API validate quan hệ giữa hai ngưỡng.
    \item API lưu thresholds và ghi audit.
\end{enumerate} \\
Luồng thay thế & Nếu threshold ngoài khoảng cho phép hoặc review floor lớn hơn auto-approve, API trả 422. \\
\bottomrule
\end{longtable}

\subsection[UC-THRESHOLD-PREVIEW]{UC19 - Preview threshold impact}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Admin. \\
Tiền điều kiện & Admin đã đăng nhập; có predictions để tính phân phối tác động. \\
Hậu điều kiện & Admin xem được Auto-ready, Manual review và Escalate theo threshold nháp mà chưa lưu rule. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Admin chỉnh threshold nháp.
    \item Admin bấm Preview impact.
    \item UI gửi \texttt{POST /admin/ops/thresholds/preview}.
    \item API tính phân phối confidence trên dữ liệu hiện có.
    \item UI hiển thị các nhóm impact.
\end{enumerate} \\
Luồng thay thế & Nếu threshold không hợp lệ, API trả 422. Nếu chưa có prediction, preview trả phân phối rỗng hoặc giá trị 0. \\
\bottomrule
\end{longtable}

\subsection[UC-ADMIN-PROMOTE-MODEL]{UC20 - Promote model từ Admin Ops}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Admin. \\
Tiền điều kiện & Admin đã đăng nhập; có candidate model run hợp lệ trong artifacts. \\
Hậu điều kiện & Candidate run được đặt làm active model package cho các lần inference sau. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Admin mở Deployment snapshot trong Admin Ops.
    \item Admin bấm Promote cho candidate model run.
    \item UI gửi \texttt{POST /admin/ops/model-runs/\{run\_id\}/activate}.
    \item API validate model run và artifact.
    \item API cập nhật active model metadata.
\end{enumerate} \\
Luồng thay thế & Nếu run id không tồn tại hoặc artifact thiếu file bắt buộc, API trả 404 hoặc lỗi validate. \\
\bottomrule
\end{longtable}

\subsection[UC-MONITORING-DASHBOARD]{UC21 - Xem Monitoring dashboard}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Data Scientist. \\
Tiền điều kiện & Data Scientist đã đăng nhập. \\
Hậu điều kiện & Dashboard hiển thị tình trạng chất lượng mô hình và các slice vận hành. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Data Scientist mở Monitoring.
    \item UI gửi \texttt{GET /scientist/monitoring}.
    \item API kiểm tra role Data Scientist.
    \item API trả stats, macro series, per-label F1, confusion matrix, slice analysis và per-class metrics.
    \item UI hiển thị monitoring dashboard.
\end{enumerate} \\
Luồng thay thế & Nếu chưa có reviewed predictions, UI hiển thị empty state hoặc N/A ở các metric phụ thuộc decision. \\
\bottomrule
\end{longtable}

\subsection[UC-MONITORING-RECOMPUTE-ASYNC]{UC22 - Recompute monitoring qua worker}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Data Scientist, worker-service, worker scheduler. \\
Tiền điều kiện & Redis và worker-service đang hoạt động; Data Scientist có token hợp lệ hoặc scheduler được bật. \\
Hậu điều kiện & Worker job \texttt{monitoring\_recompute} hoàn tất; monitoring snapshot được cập nhật. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Data Scientist bấm Recompute hoặc scheduler kích hoạt cron.
    \item API tạo worker job qua \texttt{POST /scientist/monitoring/jobs/recompute}.
    \item Job được enqueue vào Redis.
    \item Worker consume job và tính lại monitoring.
    \item Worker lưu trạng thái, result và snapshot mới.
    \item UI poll job rồi fetch lại dashboard.
\end{enumerate} \\
Luồng thay thế & Nếu enqueue thất bại, API đánh dấu job failed và trả 503. Nếu worker lỗi, job lưu status failed kèm error. \\
\bottomrule
\end{longtable}

\subsection[UC-MODEL-VERSIONS]{UC23 - Xem Model Versions}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Data Scientist. \\
Tiền điều kiện & Data Scientist đã đăng nhập; artifacts directory có ít nhất active run hoặc UI xử lý được trạng thái rỗng. \\
Hậu điều kiện & Data Scientist thấy model runs, selected run, package details, confusion matrix và export files. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Data Scientist mở Model Versions.
    \item UI gửi \texttt{GET /scientist/model-versions}.
    \item API đọc metadata và artifact files.
    \item API trả runs, selected run, comparison cards, confusion matrix, package details và exports.
    \item UI hiển thị bảng uploaded runs và panel chi tiết.
\end{enumerate} \\
Luồng thay thế & Nếu selected run id không tồn tại, API trả 404. Nếu chưa có artifact, UI hiển thị trạng thái rỗng. \\
\bottomrule
\end{longtable}

\subsection[UC-MODEL-UPLOAD]{UC24 - Upload artifact}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Data Scientist. \\
Tiền điều kiện & Data Scientist đã đăng nhập; artifact được đóng gói đúng cấu trúc hoặc chọn đủ file bắt buộc. \\
Hậu điều kiện & Model run mới được lưu trong artifacts directory và metadata được cập nhật. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Data Scientist nhập run ID và upload label.
    \item Data Scientist chọn một file zip hoặc nhiều artifact files.
    \item UI gửi multipart form đến \texttt{POST /scientist/model-versions/upload}.
    \item API kiểm tra config, label config, checkpoint và tokenizer files.
    \item API lưu artifact, đọc metrics/confusion matrix và trả metadata model run.
\end{enumerate} \\
Luồng thay thế & Nếu thiếu file bắt buộc, checkpoint hoặc tokenizer, API trả lỗi validate. Nếu run ID không hợp lệ, API từ chối upload. \\
\bottomrule
\end{longtable}

\subsection[UC-MODEL-ACTIVATE]{UC25 - Activate artifact}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Data Scientist. \\
Tiền điều kiện & Data Scientist đã đăng nhập; model run tồn tại và artifact hợp lệ. \\
Hậu điều kiện & Model run được đặt làm active package. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Data Scientist chọn một model run.
    \item Data Scientist bấm Set as active.
    \item UI gửi \texttt{POST /scientist/model-versions/\{run\_id\}/activate}.
    \item API validate run và cập nhật active model.
    \item UI reload Model Versions để hiển thị trạng thái active mới.
\end{enumerate} \\
Luồng thay thế & Nếu run không tồn tại, API trả 404. Nếu artifact thiếu file bắt buộc, API trả lỗi validate. \\
\bottomrule
\end{longtable}

\subsection[UC-MODEL-EXPORT-DOWNLOAD]{UC26 - Download export}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Data Scientist. \\
Tiền điều kiện & Data Scientist đã đăng nhập; selected run có export file hợp lệ. \\
Hậu điều kiện & File export được tải về trình duyệt để kiểm tra hoặc triển khai. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Data Scientist mở Model Versions và chọn run.
    \item UI hiển thị danh sách export chips.
    \item Data Scientist chọn một export file.
    \item UI gửi \texttt{GET /scientist/model-versions/\{run\_id\}/exports/\{filename\}}.
    \item API validate filename và trả file response.
\end{enumerate} \\
Luồng thay thế & Nếu filename không thuộc exports của run hoặc có path traversal, API trả 404. Nếu token không hợp lệ, API trả 401. \\
\bottomrule
\end{longtable}

\subsection[UC-DATASET-LAB]{UC27 - Dataset Lab}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & Data Scientist. \\
Tiền điều kiện & Data Scientist đã đăng nhập; hệ thống có articles/predictions để phân tích dataset. \\
Hậu điều kiện & Data Scientist nhìn thấy tình trạng dataset, hard samples và tín hiệu active learning. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Data Scientist mở Dataset Lab.
    \item UI gửi \texttt{GET /scientist/dataset-lab}.
    \item API tổng hợp stored articles, low-confidence pool, label imbalance, hard samples và priority labels.
    \item UI hiển thị stats, progress list, sample list và active-learning loop.
\end{enumerate} \\
Luồng thay thế & Nếu chưa có data, UI hiển thị empty state cho hard samples hoặc priority labels. Nếu token không hợp lệ, API trả 401. \\
\bottomrule
\end{longtable}

\subsection[UC-HEALTH-CHECK]{UC28 - Health check runtime}

\begin{longtable}{C{0.23\textwidth}p{0.67\textwidth}}
\toprule
\textbf{Thuộc tính} & \textbf{Nội dung} \\
\midrule
Actor & System operator. \\
Tiền điều kiện & Docker Compose stack hoặc deployment runtime đang chạy. \\
Hậu điều kiện & Operator biết API, database và model-service có sẵn sàng trước khi demo/test hay không; Redis/worker được xác nhận qua worker job/runtime. \\
Luồng chính & \begin{enumerate}[leftmargin=*,nosep]
    \item Operator gọi \texttt{GET /health}.
    \item API kiểm tra kết nối Postgres.
    \item API gọi health check của model-service.
    \item API trả status tổng, database status, model-service status, active model version và latency.
    \item Operator kiểm tra Redis/worker qua Docker Compose hoặc trạng thái worker jobs khi cần.
\end{enumerate} \\
Luồng thay thế & Nếu database hoặc model-service không sẵn sàng, health trả trạng thái lỗi tương ứng. Nếu Redis/worker lỗi, các use case async sẽ failed hoặc job không được enqueue. \\
\bottomrule
\end{longtable}
```

## Source of truth cho lượt test

- Thời điểm capture lại: 17/05/2026 khoảng 04:32 ICT.
- Công cụ capture: Chromium automation.
- Cách chụp: đợi `networkidle`, đợi font render, tắt animation `.reveal`, rồi mới screenshot để tránh ảnh còn fade/render dở.
- Runtime thật: React/Vite UI, FastAPI API-service, Dramatiq worker, Redis, Postgres, gRPC model-service.
- Artifact active: `PhoBERT package run_1777197420559`.
- Metric artifact: macro-F1 `0.9016`, weighted-F1 `0.9085`, accuracy `0.9086`.
- Health check: database `ok`, model_service `ok`, model_version `active`, latency khoảng `294ms`.
- DB kiểm tra sạch: không còn record placeholder không inference hoặc confidence bằng `0`.
- Tổng article hiện tại: `13`.
- Stored predictions hiện tại: `15`.

## Dữ liệu VietnamNet thật đã import và infer

### Nhóm classified/reviewed nhiều nhãn

- `art-1778964425-f2f6bd`: `Giá vàng thế giới` -> `Kinh doanh`, confidence `0.9739`, status `approved`.
- `art-1778964426-345197`: `Man City đấu Arsenal, League Cup: Tất cả chống lại Pep Guardiola` -> `Thể thao`, confidence `0.9984`, status `approved`.
- `art-1778964427-a06803`: `Cầu cứu bác sĩ vì trào lưu uống một loại nước giảm cân` -> model prediction `Thị trường tiêu dùng`, confidence `0.5030`; human override sang `Sức khỏe`.
- `art-1778964428-c666ad`: `Ám ảnh AI đẩy hàng triệu nhân viên công sở Trung Quốc vào cuộc chiến sinh tồn` -> `Công nghệ`, confidence `0.9845`, status `approved`.
- `art-1778964429-9c76a8`: `Đập kính ô tô trộm tài sản, kẻ có 6 tiền án sa lưới` -> `Pháp luật`, confidence `0.9946`, status `auto_approved`.

### Nhóm Open Review Queue thật từ model-service

- `art-1778966625-4cde88`: `BHYT cho trẻ em dưới 6 tuổi: Miễn phí, quyền lợi, cách làm` -> `Bạn đọc`, confidence `0.7301`, margin `0.4778`, status `review`, latency `161ms`.
- `art-1778966624-5d2f83`: `Hàng chục viên nam châm kết thành chuỗi gây thủng ruột bé trai 5 tuổi` -> `Đời sống`, confidence `0.4945`, margin `0.1147`, status `escalated`, latency `207ms`.
- `art-1778966622-4a8791`: `Cầu cứu bác sĩ vì trào lưu uống một loại nước giảm cân` -> `Thị trường tiêu dùng`, confidence `0.5030`, margin `0.1016`, status `escalated`, latency `166ms`.
- Review Queue hiện `Showing 3 of 3 open stories`.

### Monitoring / Dataset Lab

- Monitoring snapshot: `snapshot 10`.
- Macro F1 `0.67`, Error share `0.20`, Drift score `0.10`, Coverage `69%`.
- Article analysis: `Open review queue = 3`, `Reviewed predictions = 5`, `Stored predictions = 15`.
- Per-label F1 có 6 nhãn: `Công nghệ`, `Kinh doanh`, `Pháp luật`, `Sức khỏe`, `Thể thao`, `Thị trường tiêu dùng`.
- Dataset Lab có `13` stored articles, low-confidence pool `13`.
- Label imbalance có nhiều nhãn: `Dân tộc - Tôn giáo`, `Sức khỏe`, `Thể thao`, `Pháp luật`, `Công nghệ`, `Kinh doanh`, `Bạn đọc`, `Thị trường tiêu dùng`.
- Latest recompute worker job: `job-1778967139-38d1127b`, `monitoring_recompute`, status `completed`, created by `scientist@vnn-lab.edu.vn`.

## Ảnh source bài báo thật

Dùng các ảnh này để chứng minh test data đến từ bài VietnamNet thật, không phải input tự chế:

| Bài báo | Article id | Minh chứng |
|---|---|---|
| BHYT cho trẻ em dưới 6 tuổi | `art-1778966625-4cde88` | `test-report-assets-full/01-source-vietnamnet-article.png` |
| Giá vàng thế giới | `art-1778964425-f2f6bd` | `test-report-assets-full/27-source-vietnamnet-gia-vang.png` |
| Man City đấu Arsenal | `art-1778964426-345197` | `test-report-assets-full/28-source-vietnamnet-man-city.png` |
| Cầu cứu bác sĩ vì trào lưu giảm cân | `art-1778964427-a06803` và `art-1778966622-4a8791` | `test-report-assets-full/29-source-vietnamnet-giam-can.png` |
| Ám ảnh AI công sở Trung Quốc | `art-1778964428-c666ad` | `test-report-assets-full/30-source-vietnamnet-ai-cong-so.png` |
| Đập kính ô tô trộm tài sản | `art-1778964429-9c76a8` | `test-report-assets-full/31-source-vietnamnet-phap-luat.png` |
| Bé trai nuốt nam châm | `art-1778966624-5d2f83` | `test-report-assets-full/32-source-vietnamnet-nam-cham.png` |

## Coverage matrix theo use case

Trong report, hãy dùng bảng này để tránh claim sai. Cột `Mức bằng chứng` nên giữ nguyên hoặc diễn đạt tương đương.

| Use case | Mức bằng chứng | Kết luận được phép ghi | Minh chứng |
|---|---|---|---|
| UC01 | Full UI evidence | Đăng nhập theo role Editor/Admin/Data Scientist hoạt động. | `02-auth-login-editor-selected.png`, `11-auth-login-admin-selected.png`, `16-auth-login-scientist-selected.png` |
| UC02 | Not executed in this capture | Không mark pass. Chỉ ghi logout là chức năng có trong hệ thống nếu cần. | Không có screenshot riêng |
| UC03 | Full UI evidence | Editor dashboard hiển thị đúng role, active model, stats và menu. | `03-editor-dashboard-empty-state.png` |
| UC04 | UI input evidence | Form import cho phép nhập source URL/title/content. | `04-editor-import-vietnamnet-url-form.png` |
| UC05 | Partial evidence | App có cơ chế import bất đồng bộ qua worker; lượt capture dùng dữ liệu đã import/infer thật, không claim tạo job import mới. | `05-editor-import-vietnamnet-job-complete.png` |
| UC06 | Observed UI behavior | Dashboard đọc lại kết quả import/inference đã lưu; job polling là cơ chế nội bộ của flow import. | `05-editor-import-vietnamnet-job-complete.png` |
| UC07 | Full UI evidence | Review Queue hiển thị 3 bài thật đang review/escalated. | `06-editor-review-queue-vietnamnet.png`, `25-editor-open-review-queue-records.png` |
| UC08 | Full UI evidence | Article detail hiển thị content, source URL, prediction, candidates và history. | `08-editor-article-detail-open-review.png`, `22-editor-article-detail-multi-label-low-confidence.png`, `26-editor-open-review-detail-real-inference.png` |
| UC09 | Full data evidence | Các bài đã có prediction thật từ PhoBERT model-service, có confidence/margin/latency. | `08-editor-article-detail-open-review.png`, `26-editor-open-review-detail-real-inference.png` |
| UC10 | Not executed in this capture | Không mark pass refresh URL rồi inference. | Không có screenshot riêng |
| UC11 | Persisted decision evidence | Có record approved/auto_approved được đọc lại. Không cần nói đã click approve trong lượt capture này. | `10-editor-label-review-approved.png`, `21-editor-label-review-multi-label.png` |
| UC12 | Persisted decision evidence | Có record overridden từ model prediction sang human label. | `21-editor-label-review-multi-label.png`, `23-scientist-monitoring-multi-label.png` |
| UC13 | Persisted queue evidence | Có record escalated với confidence thấp trong Review Queue và Article Detail. | `22-editor-article-detail-multi-label-low-confidence.png`, `25-editor-open-review-queue-records.png` |
| UC14 | Full UI evidence | Label Review có nhiều nhãn, không chỉ một class. | `07-editor-label-review-vietnamnet.png`, `21-editor-label-review-multi-label.png`, `10-editor-label-review-approved.png` |
| UC15 | Full UI evidence | Admin Ops hiển thị users, audit log, routing/deployment overview. | `12-admin-ops-overview.png` |
| UC16 | UI form evidence only | Form create user mở được; không claim đã tạo user mới. | `13-admin-create-user-form.png` |
| UC17 | UI form evidence only | Form edit user mở được; không claim đã update user. | `14-admin-edit-user-form.png` |
| UC18 | UI control evidence only | Threshold controls hiển thị; không claim đã lưu threshold mới. | `15-admin-threshold-preview.png` |
| UC19 | Full UI evidence | Preview threshold impact chạy và hiển thị Auto-ready/Manual review/Escalate. | `15-admin-threshold-preview.png` |
| UC20 | Not executed in this capture | Không mark pass promote model từ Admin Ops. | Không có screenshot/action riêng |
| UC21 | Full UI evidence | Monitoring dashboard hiển thị snapshot, macro F1, drift và per-label metrics. | `17-scientist-monitoring-before-recompute.png`, `23-scientist-monitoring-multi-label.png` |
| UC22 | Full UI + worker evidence | Recompute qua worker completed và dashboard cập nhật snapshot. | `18-scientist-monitoring-after-recompute.png`, `23-scientist-monitoring-multi-label.png`; job `job-1778967139-38d1127b` |
| UC23 | Full UI evidence | Model Versions hiển thị active run, F1 và package details. | `19-scientist-model-versions.png` |
| UC24 | UI control evidence only | Upload artifact control hiển thị; không claim upload mới. | `19-scientist-model-versions.png` |
| UC25 | UI control evidence only | Set as active control hiển thị; không claim activate artifact mới. | `19-scientist-model-versions.png` |
| UC26 | UI control evidence only | Export chips/download controls hiển thị; không claim đã download. | `19-scientist-model-versions.png` |
| UC27 | Full UI evidence | Dataset Lab hiển thị stored articles, low-confidence pool, label imbalance và hard samples. | `20-scientist-dataset-lab.png`, `24-scientist-dataset-lab-multi-label.png` |
| UC28 | Full API evidence | Health check xác nhận API/database/model-service ok. | `00-api-health-model-service.png` |

## Test report cần đưa vào report

Không viết đoạn văn narrative kiểu "đã kiểm thử bằng công cụ X". Thay vào đó, tạo một test report chuẩn dạng bảng. Bảng phải có các cột: `Test case ID`, `Use case`, `Actor`, `Precondition`, `Test steps`, `Expected result`, `Actual result`, `Status`, `Evidence`. Cột `Evidence` phải chứa đường dẫn hình minh chứng tương ứng để Prism chèn hoặc đặt caption ngay cạnh testcase.

Quy ước status:

- `Pass`: đã chạy/quan sát đủ expected result trong lượt capture này.
- `Observed`: chỉ xác nhận UI/control/dữ liệu persisted đã tồn tại, không thực thi action thay đổi trạng thái trong lượt capture.
- `Not executed`: không chạy trong lượt capture; đưa vào test backlog, không tính pass.

Dùng bảng test report sau cho mục `5.3.1 Kết quả kiểm thử chức năng`:

| Test case ID | Use case | Actor | Precondition | Test steps | Expected result | Actual result | Status | Evidence |
|---|---|---|---|---|---|---|---|---|
| TC-001 | UC28 | System operator | Docker Compose stack đang chạy. | Gọi API health trước khi kiểm thử UI. | API trả `status=ok`; database ok; model-service ok; model version active. | Health trả `ok`, database `ok`, model_service `ok`, model_version `active`, latency khoảng `294ms`. | Pass | `test-report-assets-full/00-api-health-model-service.png` |
| TC-002 | UC01 | Editor | Tài khoản Editor bootstrap tồn tại. | Mở login, chọn role Editor, nhập email/password. | Login form chọn đúng role Editor và sẵn sàng nhận submit. | Màn hình login hiển thị role Editor, email Editor và password field. | Pass | `test-report-assets-full/02-auth-login-editor-selected.png` |
| TC-003 | UC03 | Editor | Editor đã đăng nhập. | Submit login Editor và mở dashboard. | Dashboard hiển thị đúng role, active model, form import và editorial queue. | Editor dashboard hiển thị active model, stats, import article, editorial queue và sidebar Editor. | Pass | `test-report-assets-full/03-editor-dashboard-empty-state.png` |
| TC-004 | UC04 | Editor | Editor ở dashboard. | Nhập source URL VietnamNet vào form import. | Form chấp nhận URL bài báo thật để đưa vào pipeline. | Form Source URL chứa URL VietnamNet thật; các field title/content sẵn sàng nhập thủ công khi cần. | Pass | `test-report-assets-full/04-editor-import-vietnamnet-url-form.png` |
| TC-005 | UC05, UC06 | Editor | Dữ liệu VietnamNet đã được import/infer qua pipeline thật. | Kiểm tra dashboard sau khi dữ liệu import/inference được lưu. | Dashboard đọc lại article/prediction đã lưu, không dùng mock. | Dashboard hiển thị dữ liệu import/inference đã persist; không còn record placeholder confidence `0`. | Observed | `test-report-assets-full/05-editor-import-vietnamnet-job-complete.png` |
| TC-006 | UC07 | Editor | Có 3 bài status review/escalated trong DB. | Mở Review Queue. | Queue hiển thị các bài cần duyệt với label, confidence, margin, status và action Open. | Review Queue hiển thị 3 bài VietnamNet thật, confidence `0.73`, `0.49`, `0.50`. | Pass | `test-report-assets-full/06-editor-review-queue-vietnamnet.png`, `test-report-assets-full/25-editor-open-review-queue-records.png` |
| TC-007 | UC08, UC09 | Editor | Bài `BHYT...` tồn tại trong Review Queue. | Mở Article Detail của bài `BHYT...`. | Detail hiển thị source URL, content, prediction summary, confidence, candidates và decision controls. | Detail hiển thị prediction `Bạn đọc`, confidence `0.73`, candidates, threshold bands và controls Approve/Override/Escalate. | Pass | `test-report-assets-full/08-editor-article-detail-open-review.png`, `test-report-assets-full/26-editor-open-review-detail-real-inference.png` |
| TC-008 | UC08, UC13 | Editor | Có bài low-confidence/escalated. | Mở detail bài nam châm confidence thấp. | Bài confidence thấp được route escalated và vẫn hiển thị đầy đủ prediction/candidates. | Bài nam châm có confidence `0.49`, status `escalated`, chứng minh review-floor hoạt động. | Pass | `test-report-assets-full/22-editor-article-detail-multi-label-low-confidence.png` |
| TC-009 | UC14 | Editor | Có nhiều bài đã classified/decided. | Mở Label Review. | Label Review hiển thị danh sách bài có label, confidence, margin và status. | Label Review hiển thị các bài classified và trạng thái quyết định. | Pass | `test-report-assets-full/07-editor-label-review-vietnamnet.png` |
| TC-010 | UC14 | Editor | Đã import/infer nhiều bài khác nhãn. | Mở Label Review sau lượt bổ sung nhiều nhãn. | Danh sách không chỉ có một class; có nhiều label nghiệp vụ. | Label Review hiển thị `Pháp luật`, `Công nghệ`, `Thị trường tiêu dùng`, `Thể thao`, `Kinh doanh`. | Pass | `test-report-assets-full/21-editor-label-review-multi-label.png` |
| TC-011 | UC11, UC12, UC13 | Editor | Hệ thống đã có decisions persisted. | Kiểm tra Label Review và Monitoring để xác nhận decision states. | Decisions approved, auto-approved, overridden và escalated được đọc lại từ dữ liệu lưu. | Có record `approved`, `auto_approved`, `overridden`, `escalated`; lượt capture không click submit decision mới. | Observed | `test-report-assets-full/10-editor-label-review-approved.png`, `test-report-assets-full/21-editor-label-review-multi-label.png`, `test-report-assets-full/23-scientist-monitoring-multi-label.png` |
| TC-012 | UC10 | Editor | Article tồn tại và có source URL. | Refresh URL rồi inference lại. | Nội dung được crawl lại từ URL, prediction mới được lưu. | Không chạy trong lượt capture này để tránh thay đổi dữ liệu demo. | Not executed | Không có ảnh minh chứng. |
| TC-013 | UC01 | Admin | Tài khoản Admin bootstrap tồn tại. | Mở login, chọn role Admin, nhập email/password. | Login form chọn đúng role Admin. | Màn hình login hiển thị role Admin và credentials Admin. | Pass | `test-report-assets-full/11-auth-login-admin-selected.png` |
| TC-014 | UC15 | Admin | Admin đã đăng nhập. | Mở Admin Operations. | Admin thấy users, routing thresholds, audit log và deployment snapshot. | Admin Ops hiển thị Users & permissions, Confidence routing, Audit log và Deployment snapshot. | Pass | `test-report-assets-full/12-admin-ops-overview.png` |
| TC-015 | UC16 | Admin | Admin ở Admin Ops. | Mở form Create user. | Form cho nhập email, name, role, queue và temporary password. | Form Create user mở đầy đủ field. Không submit tạo user mới trong lượt capture. | Observed | `test-report-assets-full/13-admin-create-user-form.png` |
| TC-016 | UC17 | Admin | Admin ở Admin Ops và có user trong bảng. | Mở form Edit user. | Form cho sửa name, role, queue, status và password. | Form Edit user mở đầy đủ field. Không submit update user trong lượt capture. | Observed | `test-report-assets-full/14-admin-edit-user-form.png` |
| TC-017 | UC18, UC19 | Admin | Admin ở Admin Ops. | Điều chỉnh threshold nháp và chạy Preview impact. | Preview hiển thị Auto-ready, Manual review và Escalate to DS theo dữ liệu live. | Preview impact hiển thị đầy đủ các nhóm tác động. Không lưu threshold mới trong lượt capture. | Pass | `test-report-assets-full/15-admin-threshold-preview.png` |
| TC-018 | UC20 | Admin | Có candidate model run hợp lệ. | Promote model từ Admin Ops. | Active model được đổi sang candidate run. | Không chạy trong lượt capture này để tránh đổi active artifact. | Not executed | Không có ảnh minh chứng. |
| TC-019 | UC01 | Data Scientist | Tài khoản Data Scientist bootstrap tồn tại. | Mở login, chọn role Data Scientist, nhập email/password. | Login form chọn đúng role Data Scientist. | Màn hình login hiển thị role Data Scientist và credentials tương ứng. | Pass | `test-report-assets-full/16-auth-login-scientist-selected.png` |
| TC-020 | UC21 | Data Scientist | Data Scientist đã đăng nhập; có predictions/decisions. | Mở Monitoring dashboard trước recompute. | Dashboard hiển thị evaluation snapshot, macro F1, drift, per-label F1, confusion matrix và slice analysis. | Monitoring hiển thị snapshot hiện tại, Macro F1, Error share, Drift score, Coverage và per-label metrics. | Pass | `test-report-assets-full/17-scientist-monitoring-before-recompute.png` |
| TC-021 | UC22 | Data Scientist | Redis và worker-service đang chạy. | Bấm Recompute, đợi worker job completed, refresh dashboard. | Worker job completed; snapshot mới cập nhật trên dashboard. | Job `job-1778967139-38d1127b` completed; snapshot `10`, Macro F1 `0.67`, Open review queue `3`. | Pass | `test-report-assets-full/18-scientist-monitoring-after-recompute.png`, `test-report-assets-full/23-scientist-monitoring-multi-label.png` |
| TC-022 | UC23 | Data Scientist | Có active model artifact. | Mở Model Versions. | Trang hiển thị uploaded runs, active run, F1, confusion matrix, package details và exports. | Model Versions hiển thị active run `run_1777197420559`, macro-F1 artifact và package details. | Pass | `test-report-assets-full/19-scientist-model-versions.png` |
| TC-023 | UC24 | Data Scientist | Data Scientist ở Model Versions. | Kiểm tra Upload artifacts control. | UI có control upload và mô tả required package files. | Upload artifacts control và required package section hiển thị. Không upload artifact mới trong lượt capture. | Observed | `test-report-assets-full/19-scientist-model-versions.png` |
| TC-024 | UC25 | Data Scientist | Có selected model run. | Kiểm tra Set as active control. | UI có nút Set as active cho selected run. | Nút Set as active hiển thị. Không activate artifact mới trong lượt capture. | Observed | `test-report-assets-full/19-scientist-model-versions.png` |
| TC-025 | UC26 | Data Scientist | Selected run có export files. | Kiểm tra export/download controls. | UI hiển thị export chips có thể tải file. | Export controls hiển thị trong package details. Không download file trong lượt capture. | Observed | `test-report-assets-full/19-scientist-model-versions.png` |
| TC-026 | UC27 | Data Scientist | Hệ thống có articles/predictions. | Mở Dataset Lab. | Dataset Lab hiển thị stored articles, low-confidence pool, label imbalance, hard samples và active-learning loop. | Dataset Lab có `13` articles, low-confidence pool `13`, hard samples và nhiều label. | Pass | `test-report-assets-full/20-scientist-dataset-lab.png`, `test-report-assets-full/24-scientist-dataset-lab-multi-label.png` |
| TC-027 | UC02 | All roles | Người dùng đã đăng nhập. | Thực hiện Sign out. | Session bị xóa và UI quay về login. | Không chạy trong lượt capture này. | Not executed | Không có ảnh minh chứng. |

Sau bảng test report, thêm ghi chú ngắn: các test case `Observed` chỉ xác nhận UI/control hoặc dữ liệu persisted, chưa submit action thay đổi trạng thái trong lượt capture; các test case `Not executed` là backlog kiểm thử bổ sung, không tính vào số lượng pass.

## Độ phủ màn hình theo role

### Nguồn dữ liệu và health

| Màn hình | Mục đích | Minh chứng |
|---|---|---|
| API health | Xác nhận database và model-service đang chạy thật trước khi test UI. | `test-report-assets-full/00-api-health-model-service.png` |
| Source bài BHYT | Trang VietnamNet của bài open-review chính. | `test-report-assets-full/01-source-vietnamnet-article.png` |
| Source bài kinh doanh | Trang VietnamNet của bài `Giá vàng thế giới`. | `test-report-assets-full/27-source-vietnamnet-gia-vang.png` |
| Source bài thể thao | Trang VietnamNet của bài Man City - Arsenal. | `test-report-assets-full/28-source-vietnamnet-man-city.png` |
| Source bài sức khỏe/tiêu dùng | Trang VietnamNet của bài giảm cân. | `test-report-assets-full/29-source-vietnamnet-giam-can.png` |
| Source bài công nghệ | Trang VietnamNet của bài AI công sở. | `test-report-assets-full/30-source-vietnamnet-ai-cong-so.png` |
| Source bài pháp luật | Trang VietnamNet của bài đập kính ô tô. | `test-report-assets-full/31-source-vietnamnet-phap-luat.png` |
| Source bài đời sống | Trang VietnamNet của bài nam châm. | `test-report-assets-full/32-source-vietnamnet-nam-cham.png` |

### Editor

| Use case | Màn hình | Kết quả quan sát | Minh chứng |
|---|---|---|---|
| UC01 | Login Editor | Chọn role Editor và đăng nhập bằng tài khoản bootstrap. | `test-report-assets-full/02-auth-login-editor-selected.png` |
| UC03 | Editor Dashboard | Dashboard hiển thị active model, stats, queue và form import. | `test-report-assets-full/03-editor-dashboard-empty-state.png` |
| UC04 | Import article form | Form import điền URL VietnamNet thật. | `test-report-assets-full/04-editor-import-vietnamnet-url-form.png` |
| UC04-UC06 | Import/inference evidence | Dashboard đọc lại dữ liệu import và prediction đã lưu. | `test-report-assets-full/05-editor-import-vietnamnet-job-complete.png` |
| UC07 | Review Queue | Open Review Queue hiển thị 3 bài VietnamNet thật đã được PhoBERT infer và đang chờ editor xử lý. | `test-report-assets-full/06-editor-review-queue-vietnamnet.png`, `test-report-assets-full/25-editor-open-review-queue-records.png` |
| UC14 | Label Review | Bài classified xuất hiện trong màn hình review nhãn. | `test-report-assets-full/07-editor-label-review-vietnamnet.png` |
| UC14 | Label Review nhiều nhãn | Danh sách có nhiều nhãn: Pháp luật, Công nghệ, Thị trường tiêu dùng, Thể thao, Kinh doanh. | `test-report-assets-full/21-editor-label-review-multi-label.png` |
| UC08 | Article Detail open review | Bài `BHYT...` hiển thị prediction `Bạn đọc`, confidence `0.73`, ranking và decision controls. | `test-report-assets-full/08-editor-article-detail-open-review.png`, `test-report-assets-full/26-editor-open-review-detail-real-inference.png` |
| UC08/UC13 | Article Detail confidence thấp | Bài nam châm có confidence `0.49`, status `escalated`, chứng minh review-floor hoạt động. | `test-report-assets-full/22-editor-article-detail-multi-label-low-confidence.png` |
| UC11-UC13 | Decision persisted | Label Review hiển thị các record đã được approve/override/escalated. | `test-report-assets-full/10-editor-label-review-approved.png` |

### Admin

| Use case | Màn hình | Kết quả quan sát | Minh chứng |
|---|---|---|---|
| UC01 | Login Admin | Chọn role Admin tại login. | `test-report-assets-full/11-auth-login-admin-selected.png` |
| UC15 | Admin Operations | Hiển thị users, routing rules, audit log, deployment snapshot. | `test-report-assets-full/12-admin-ops-overview.png` |
| UC16 | Create User | Form mời user mới được mở. | `test-report-assets-full/13-admin-create-user-form.png` |
| UC17 | Edit User | Form cập nhật role, queue, status, password được mở. | `test-report-assets-full/14-admin-edit-user-form.png` |
| UC18-UC19 | Threshold Preview | Preview impact đọc phân phối confidence từ dữ liệu live. | `test-report-assets-full/15-admin-threshold-preview.png` |

### Data Scientist

| Use case | Màn hình | Kết quả quan sát | Minh chứng |
|---|---|---|---|
| UC01 | Login Data Scientist | Chọn role Data Scientist tại login. | `test-report-assets-full/16-auth-login-scientist-selected.png` |
| UC21 | Monitoring trước recompute | Dashboard monitoring hiển thị snapshot/chỉ số hiện tại. | `test-report-assets-full/17-scientist-monitoring-before-recompute.png` |
| UC22 | Monitoring recompute worker | Snapshot sau recompute hiển thị nhiều nhãn, confusion matrix, per-class metrics và Open review queue. | `test-report-assets-full/18-scientist-monitoring-after-recompute.png`, `test-report-assets-full/23-scientist-monitoring-multi-label.png` |
| UC23-UC26 | Model Versions | Hiển thị active package, F1, confusion matrix 19x19, package details và controls upload/activate/export. | `test-report-assets-full/19-scientist-model-versions.png` |
| UC27 | Dataset Lab | Hiển thị label imbalance nhiều nhãn, hard samples, override queue và relabel batch. | `test-report-assets-full/20-scientist-dataset-lab.png`, `test-report-assets-full/24-scientist-dataset-lab-multi-label.png` |

## Danh sách hình cần chèn

![Health check API và model-service](test-report-assets-full/00-api-health-model-service.png)

![Source VietnamNet của bài BHYT trong Open Review](test-report-assets-full/01-source-vietnamnet-article.png)

![Source VietnamNet của bài giá vàng](test-report-assets-full/27-source-vietnamnet-gia-vang.png)

![Source VietnamNet của bài thể thao](test-report-assets-full/28-source-vietnamnet-man-city.png)

![Source VietnamNet của bài giảm cân](test-report-assets-full/29-source-vietnamnet-giam-can.png)

![Source VietnamNet của bài công nghệ AI công sở](test-report-assets-full/30-source-vietnamnet-ai-cong-so.png)

![Source VietnamNet của bài pháp luật](test-report-assets-full/31-source-vietnamnet-phap-luat.png)

![Source VietnamNet của bài nam châm](test-report-assets-full/32-source-vietnamnet-nam-cham.png)

![Login Editor](test-report-assets-full/02-auth-login-editor-selected.png)

![Dashboard Editor](test-report-assets-full/03-editor-dashboard-empty-state.png)

![Form import điền URL VietnamNet](test-report-assets-full/04-editor-import-vietnamnet-url-form.png)

![Dashboard đọc lại dữ liệu import/inference](test-report-assets-full/05-editor-import-vietnamnet-job-complete.png)

![Review Queue chứa bài VietnamNet](test-report-assets-full/06-editor-review-queue-vietnamnet.png)

![Open Review Queue có record thật từ model](test-report-assets-full/25-editor-open-review-queue-records.png)

![Label Review trước khi approve](test-report-assets-full/07-editor-label-review-vietnamnet.png)

![Label Review với nhiều nhãn sau lượt import bổ sung](test-report-assets-full/21-editor-label-review-multi-label.png)

![Chi tiết bài BHYT trong Open Review](test-report-assets-full/08-editor-article-detail-open-review.png)

![Chi tiết bài thật sau inference model-service](test-report-assets-full/26-editor-open-review-detail-real-inference.png)

![Chi tiết bài confidence thấp được route escalated](test-report-assets-full/22-editor-article-detail-multi-label-low-confidence.png)

![Label Review sau khi approve/override](test-report-assets-full/10-editor-label-review-approved.png)

![Login Admin](test-report-assets-full/11-auth-login-admin-selected.png)

![Admin Operations overview](test-report-assets-full/12-admin-ops-overview.png)

![Admin create user form](test-report-assets-full/13-admin-create-user-form.png)

![Admin edit user form](test-report-assets-full/14-admin-edit-user-form.png)

![Admin threshold preview](test-report-assets-full/15-admin-threshold-preview.png)

![Login Data Scientist](test-report-assets-full/16-auth-login-scientist-selected.png)

![Monitoring trước recompute](test-report-assets-full/17-scientist-monitoring-before-recompute.png)

![Monitoring sau recompute](test-report-assets-full/18-scientist-monitoring-after-recompute.png)

![Monitoring với nhiều nhãn và open review queue](test-report-assets-full/23-scientist-monitoring-multi-label.png)

![Model Versions và active artifact](test-report-assets-full/19-scientist-model-versions.png)

![Dataset Lab overview](test-report-assets-full/20-scientist-dataset-lab.png)

![Dataset Lab với label imbalance nhiều nhãn](test-report-assets-full/24-scientist-dataset-lab-multi-label.png)

## Ghi chú LaTeX

- Dùng `\includegraphics[width=\textwidth]{...}` cho các ảnh dashboard/full page.
- Với source article, có thể dùng `width=0.92\textwidth` nếu ảnh quá cao hoặc đưa vào phụ lục.
- Caption nên gắn với use case, ví dụ: `Open Review Queue hiển thị ba bài VietnamNet thật đã được PhoBERT infer`.
- Nếu report cần gọn, ưu tiên 10 hình chính: health, một source article, review queue, review detail, low-confidence detail, label review nhiều nhãn, admin overview, monitoring after recompute, model versions, dataset lab.
- Không đưa `capture-results-full.json` vào report chính; file đó chỉ là log kiểm chứng.
