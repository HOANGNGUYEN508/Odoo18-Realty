Hoàng: phân tích và thiết kế hệ thống.

⭐️ Spring 1:

    - Thêm các list model:
        + Hiếu:
            * Mục đính mua.
            * Đặc điểm BDS.
        + Khải:
            * Chức danh.
            * Phân Quyền Chức Danh.
        + Huy:
            * Hướng Nhà.
            * Group Hướng Nhà.
            * Khu vực.
            * Tỉnh/TP.
            * Phường/xã.
            * Quận/huyện.
        + Hoàng:
            * Hiện Trạng.
            * Tag.
            * Loại Hình.
            * Policy.
    - Tạm thời không để ý đến link giữa module nhỏ và lớn nhưng phải link FK giữa các list module nếu có.

🌟 Báo cáo - Spring 1:

    - Hiếu:
        + Mục đính mua. ✅
        + Đặc điểm BDS. ✅
    - Khải:
        + Chức danh. ✅
        + Phân Quyền Chức Danh. ✅
    - Huy:
        + Hướng Nhà. ✅
        + Group Hướng Nhà. ✅
        + Khu vực, Tỉnh/TP, Phường/xã, Quận/huyện. ❌
    - Hoàng:
        + Hiện Trạng. ✅
        + Tag. ✅
        + Loại Hình. ✅
        + Policy. ✅

⭐️ Spring 2:

    - Models:
        + User: Huy + Khải.
        + Product: Hiếu + Hoàng.
    - Tasks:
        + Giao Diện: Views.
            * Admin: cấp cao -> thấp.
            * User: Ứng viên, chuyên viên, đầu chủ, trưởng phòng , trợ lý.
        + Backend
            * Thêm các trường dữ liệu.
            * Ẩn những chức năng và trường dữ liệu ko liên quan.
            * Phân quyền.
            * Thao tác: Method.
        + Link model - kết nối FK: kết nối FK giữa các list model nhỏ và module lớn.

🌟 Báo cáo - Spring 2:

      - Company Isolation: Người dùng từ các công ty khác chỉ có thể tương tác với dữ liệu của riêng họ, nhưng vẫn có thể đọc dữ liệu gốc của công ty cơ sở; họ không thể tạo, cập nhật hoặc xóa (CUD) dữ liệu đó.
      - Mọi model trong module realty_bds sẽ có 2 view cơ bản: list, form
      - Huy:
          + Khu vực, Tỉnh/TP, Phường/xã, Quận/huyện. ✅
          + Chuyển Tỉnh/TP từ model tự tạo sang sử dụng model res.country.state của Odoo.
          + Tách Tỉnh/TP, Phường/xã, Quận/huyện sang thành module hành chính Việt Nam.
      - Khải:
          + Chỉnh sửa model res.users, res.partner, res.company.
          + signup: chỉnh sửa sign_up template (xml + controller + js).
          + Thêm và chỉnh sửa model hr.department của odoo.
          + Thêm data vào res.groups với mỗi model cần phân quyền.
          + Thêm data vào ir.rule ứng với mỗi group trong data thêm vào res.groups để đạt được Company Isolation.
          + Thêm data vào ir.model.access.csv ứng với mỗi group.
          + Chuyển model chức danh sang sử dụng hr.job của odoo .
          + Thêm wizard để thêm employee vô department từ form view của department
          + Thêm wizard để tạo user cơ bản với chức danh.
          + Chuẩn hóa code nhánh user -> merge source -> push lên main.
      - Phương:
          + Chỉnh sửa trang cá nhân.
          + my_profile: thêm tính năng đổi mật khẩu tại trang cá nhân (xml + js + css + controller).
      - Hoàng:
          + Thêm model unit_price, land_tittle.
          + Thêm và chỉnh sửa model product.template của odoo, thêm kanban view.
          + filter: Custom hoàn toàn filter mới thay cho filter truyền thống của odoo bởi filter này khó sử dụng cho những người không thạo với máy tính. Những tính năng của filter:
              * Chọn trường với những dropdown của many2one hoặc many2many, điền trường với 2 input field (max price, min price) -> nhấn Apply Filters để lọc domain của view (list hoặc kanban), nhấn Reset để domain của view về ban đầu.
              * Thêm model method vào ir.filters để người dùng có thể lưu preference của filter hiện tại, có thể chọn để lọc theo những trường đã lưu. Có thể chọn preference là default filter để ngay khi vừa vào view sẽ load domain của default filter. Có thể xóa bất kì preference nào đã lưu ngay tại dropdown chọn preference.
              * Thay thế odoo search_bar bằng tag field - khi nhấn Apply Filters, những trường được lọc sẽ xuất hiện dưới dạng các tag, có thể loại bỏ các tag khi nhấn vào x bên phải chúng và khi ấy domain sẽ dược filter tương ứng. Tag sẽ chỉ có 1 loại duy nhất xuất hiện, 1 là preference tag hay là tag cho các trường lẻ.
          + photo_lightbox: custom component để sử dụng cho many2many_image - dùng để xem hình ảnh với kích thước nguyên bản của chúng; có những chức năng set ảnh đại diện, download và delete ảnh. Không thể dùng tính năng kéo thả ảnh khi lightbox đang hiện diện.
          + validated_file_input: nâng cấp component fileinput của odoo để support tính năng kéo thả ảnh dùng cho many2many_image. Thêm tính năng validata file - chỉ chấp nhận file dạng image, tối đa 5 bức ảnh dược upload mỗi bất động sản (ex: upload 7 file - file thứ 4 gặp vấn đề -> chấp nhận file 1 - 3, 5 và 6; bỏ file thứ 4 do bi lỗi và thứ 7 do vượt quá số lượng cho phép), tối đa 5 MB mỗi file upload.
          + Custom field widget:
              * many2many_chip: thay thế field widget many2many_tags của odoo nhưng chỉ là readonly, sử dụng trong list view của product.template và filter bên trên. Name của những ảnh upload lên sẽ được hash lại thông qua sự kết hợp của controller và trường được cài vào ir.config_parameter.
              * many2many_image: nâng cấp many2many_binary của odoo với việc trình bày hình ảnh được upload cụ thể đưới dạng scale nhỏ của chúng. User có thể set ảnh đại diện trong số những ảnh upload lên để thẻ kanban sẽ sử dụng ảnh đó làm đại diện cho bất dộng sản. Thêm tính năng kéo thả ảnh vào ô trình bày ảnh để upload.
          + Thêm:
              * 1 vài trường vào những model bên nhánh user.
              * constrain vào những model của module hành chính Việt Nam.
              * data cho hr.job: tạo ra 2 chức danh là Realty Super User (với quyền hạn về cơ bản là super user của odoo để không phải đăng nhập vô hệ thống với vai trò là super user) và admin thuộc base company (chỉ quyền điều hành những attribute model cho bất động sản).
              * data cho res.users: ngay lập tức gán chức danh Realty Super User cho user với id là 2. Note: bởi những rule thêm vào ir.rule và ir.model.access.csv, administrator ngay lập tức bị khóa khỏi việc tương tác với các model, bao gồm cả việc tương tác với hr.job dẫn đến khóa trong khóa và phải giải quyết bằng việc đăng nhập với tư cách là super user.
              * data cho unit_price: billion và million để dùng ngay lập tức.
          + Sửa:
              * Override create, write method của res.users và hr.employee.
              * data của res.groups, ir.rule, ir.model.access.csv để có thể hoàn toàn đạt được tính năng company isolation (phần Khải chỉ có khiến người của công ty tương tác với record của công ty).
          + Chuẩn hóa code nhánh product + code của Phương -> merge source -> push lên main.

🌟 Báo cáo - Spring 3:

      - Hoàng:
          + Thêm chức năng để người tạo ra record của real estate sẽ có quyền quyết định cá nhân hoặc toàn bộ cá nhân thuộc công ty khác có quyền xem record của mình.
          + Thêm tính năng readonly và presentationImage vào many2many_image và photo_lightbox (do tính năng set ảnh đại diện là custom riêng cho product.template, dùng widget cho mấy field khác không có sử dụng).
          + Thêm model: owner_feedback, client_feedback, product_report.
          + Thêm views và menu cho những model mới.
          + Hoàn thiện model action (xem lịch sử thay đổi, đặt lịch hẹn, làm report) của product.template.
          + Sửa override create tại res.users: khi tạo user mới sẽ block đi những quyền cơ bản mà odoo tự gán -> kiểm soát hoàn toàn thông qua hệ thống phân quyền ứng với chức danh của realty_bds.
    				+ Thêm hướng dẫn archive record rule với tên là 'Job multi company rule' sau khi install module realty_bds: rule mặc định của odoo khiến cho user không tạo job title cho company khác company mặc định của mình. Do đã kiểm soát chặt chẽ thông qua cơ chế assign job_title để có quyền nên không cần thiết.
          + Sửa lỗi chính tả.
          + Sửa sql_constraints khắp các model.
          + Cấu trúc lại folder: gộp các file ..._menu.xml lại với nhau. Tạo folder menu gồm các file là menu chính và các sub-menu của menu chính. Tạo folfer templates dành cho override templates của odoo.
          + Cấu trúc lại file __manifest__.py để dể dàng thêm thông tin sau này.
          + Loại bỏ help khỏi các list model.
          + Thêm abstract model notify: có chức năng giống như post của facebook.
          + Tạo 4 model cho các loại post khác nhau kế thừa notify: congratulation, guideline, notification, urgent_buying.
          + Thêm css cho notify.
          + Thêm 3 groups ứng với mỗi model kế thừa notify mới với 7 rules mỗi model để đạt được logic:

          + Thêm view: form, kanban cho user và kanban cho moderator và 2 action để gọi view (1 cái gọi form + kanban cho user, 1 cái gọi chỉ kanban cho moderator).
          + Thêm transient model notify_wizard để tiện thêm lý do khi từ chối hoặc loại bỏ post.
          + Thêm form view wizard cho notify_wizard.
          + Thêm 2 model hỗ trợ cho notify: remove_reason và reject_reason - những lựa chọn có sẵn khi muốn từ chối/loại bỏ post hoặc là tự ghi lý do riêng. moderator_guideline (list model) để cho mod biết tiêu chuẩn đánh giá post.
          + Thêm list, form view cho 2 model remove_reason và reject_reason.
          + Thêm model hỗ trợ cho notify: moderator_guideline - list những quy tắc mod cần tuân thủ khi quản lý post.
          + Thêm list, form view cho 2 model remove_reason và reject_reason.
          + Tạo js cho tính năng xem moderator_guideline tại kanban view của congratulation, guideline, notification, urgent_buying. registry dưới kiểu "views" đặt tên là info_kanban để có thể dùng cho trường js_class của kanban view (extend KanbanController để thêm button).
          + Tạo custom action (ir.actions.client) cho model realty_comment.
          + Format lại tất cả file python (trộn lẫn tab và space -> dùng space: black formatter).
          + Override lại hàm create để bắt buộc company_id là company_id của user hiện tại đang sử dụng tính năng create, bỏ sử dụng default (có thể bị set sai khi import record).
          + Thêm 1 button vào filter: favorite_list -> khi click sẽ lọc lấy tất cả những product đã được click favorite button widget -> button chuyển sang trạng thái kích hoạt -> click lại lần nữa để tắt.
          + Fix bug tại filter: dùng sai trường unit_price_units -> unit_prices.
          + Thêm hướng dẫn archive record rule với tên là 'Product multi-company': phá vỡ logic xem record product xuyên company của realty_bds.
          + Tạo controller BinaryController sao chép dựa trên controler Binary của odoo 18: fetch img không cần thông qua có set up 'allow companies' (res.users) hoặc 'is public document' (ir.attachment) để có thể xem img được gán vào record qua trường many2many. Cơ chế hoạt động: Chỉ cần user có quyền read với record mà những img đó được gán vào thì sẽ có quyền xem những img ấy.
					+ Inherit model ir.attachment để thêm các trường: orphaned_date, orphaned_from_model, orphaned_from_res_id.
          + Override unlink của product.template, product_report, notify để sau khi record bị delete thì tìm tất cả attachment (trong trường hợp này thì tất cả đều là img) được gán vào cùng với record sẽ set những trường được thêm mới của các attachment để sau này delete bằng model data_recycle.model.
					+ Sửa file 'data_recycle': thêm 3 record mới và sửa 2 record cũ theo logic mới sửa của ir.attachment.
					+ Thêm hướng dẫn vào file README.md: install module realty_bds xong tắt comment dòng 'data/data_recycle.xml', của 'data' trong file __manifest__.py rồi restart server và upgrade lại module để có tính năng tự động dọn các attachment không còn được dùng đến.