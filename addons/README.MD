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
          + Thêm 3 groups ứng với mỗi model kế thừa notify mới với 8 rules mỗi model để đạt được logic:
            * Normal user có thể read: post của company của user, approve post từ base company (company_id = 1), approve post bởi các user khác cùng company. Create post cho company của user. Chỉ edit post mà user tạo (vẫn thuộc company mà user hiện tại thuộc về) nhưng chỉ khi edit_counter khác 0. Chỉ delete post mà user tạo (vẫn thuộc company mà user hiện tại thuộc về).
            * Moderator cùng với quyền read mà user có, moderator có thể read pending post được assigned cho họ (moderator_id = user.id) thuộc company hiện tại của họ. Chỉ edit những post huộc company hiện tại của họ nếu edit_counter != 0. Những quyền này là để moderator approve post, sẽ bị giới hạn trong model.
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
          + Tạo controller BinaryController sao chép dựa trên controler Binary của odoo 18: fetch img không cần thông qua có set up 'allow companies' (res.users) hoặc 'is public document' (ir.attachment) để có thể xem img được gán vào record qua trường many2many. Cơ chế hoạt động: Chỉ cần user có quyền read với record mà những img đó được gán vào thì sẽ có quyền xem những img ấy, hoặc sẽ cho xem mà không cần bất cứ quyền gì nếu như người tạo ra attacment là người đang xem.
          + Inherit model ir.attachment để thêm các trường: orphaned_date, orphaned_from_model, orphaned_from_res_id.
          + Override unlink của product.template, product_report, notify để sau khi record bị delete thì tìm tất cả attachment (trong trường hợp này thì tất cả đều là img) được gán vào cùng với record sẽ set những trường được thêm mới của các attachment để sau này delete bằng model data_recycle.model.
          + Sửa file 'data_recycle': thêm 3 record mới và sửa 2 record cũ theo logic mới sửa của ir.attachment.
          + Thêm hướng dẫn vào file README.md: install module realty_bds xong tắt comment dòng 'data/data_recycle.xml', của 'data' trong file __manifest__.py rồi restart server và upgrade lại module để có tính năng tự động dọn các attachment không còn được dùng đến.
          + Thêm model permission_tracker để hỗ trợ cho model product.template, congratulation, guideline, notification, urgent_buying.
          + Thêm view (list, form), data file, menuitem cho permission_tracker.
          + Áp dụng @tools.ormcache vào những hàm return data cần dùng nhiều lần.
          + Update cách sử dụng model policy. 
          + Sửa code của res.partner, res.company, ir.attachment. Thêm 1 method mới là mark_true (attachment được upload thông qua many2many_images nếu không save record lại sẽ để lại các attachment với data bị khuyết - có res_model nhưng không thuộc m2m của bất kì field nào -> giải pháp: default giá trị của orphaned_from_res_id là -1, override create sau khi tạo ra see4 trỏ tới những attachment trong record mới tạo ra và chuyển orphaned_from_res_id về 0).
          + Thêm 5 rule mới vào data_cycle data file, sửa các rule cũ.
          + Sửa các model có attachment dưới dạng m2m: lúc trước override unlink để delete thì mark các attachment -> sử dụng @api.ondelete (product_report, notify, product.template).
          + Thêm hệ thống subscriber vào res.partner, làm toggle widget cho hệ thống này: boolean_subscriber (gần tương tự như widget boolean_favorite của odoo). Những user đã subscribe tới 1 user khác khi họ post bài mới trong notify sẽ được nhận thông báo trong inbox tại discuss.
          + Optimzie phương thức save_or_override_filter trong ir.filters.
          + Thêm hệ thống approval và tự động assign moderator vào product.template, thêm group moderator cho product.template (cùng với những quyền và tính năng theo cùng với hệ thống này).
          + Chỉnh sửa notify_wizard để có thể dùng cho realty_comment. 
          + Thêm ir.rule cho realty_comment: người tạo ra comment có toàn quyền với comment của mình, moderator có quyền remove comment của người khác. 
          + Thêm ir.rule cho ir.attachment: những model sử dụng attachemnt dưới dạng m2m thì moderator sẽ chỉ được xem các attachment của người khác.
          + Tạo wizard model để moderator remove comment với lý do: comment_wizard.
          + Tạo UI của realty_comment hoàn toàn thông qua js để optimize xử lý và tự do của UI: realty_comment_action, realty_comment_dialog, realty_comment_item. Cách hoạt động: notify kích hoạt comment dialog qua action_open_comments - ir.actions.client với tag realty_comment_dialog_action -> trigger action realty_comment_dialog_action -> gọi env.services.dialog -> gọi comment dialog.
            1. Tổng quan:
              * Model chính: realty_comment — hỗ trợ nested (vô hạn) bằng _parent_name, _parent_store, parent_left/right/path, ondelete="cascade".
              * Multimodel via res_model, res_id (comment dùng cho nhiều model của notify).
              * Trường quan trọng: content, create_uid, like_user_ids, like_count, child_count, is_author, client_tmp_id (context), parent_id.
              * Validation: @api.constrains, override create, write, unlink để bắt buộc client_tmp_id/create_or_reply cho create, sanitize content, check target tồn tại.
            2. Hệ thống optimistic updates (frontend):
              * Tạo tmp id: _makeTmpId() / javascript_makeTmpId() → negative IDs: -(Date.now()*1000 + counter).
              * Optimistic insert (flow)
                > _optimisticInsert(payload, client_tmp_id): sinh tmpId, tạo record tạm:
                  {
                    id: tmpId,
                    client_tmp_id,
                    content,
                    create_uid: [userId, userName],
                    like_count: 0, child_count: 0,
                    create_date: new Date().toISOString(),
                    parent_id: payload.parent_id || null,
                    pending: true, temp: true
                  }
                  chèn vào repliesByParent[parentId] hoặc topLevel (page 0 hoặc last cached page nếu page0 full).
                > lưu undo meta vào _undoMap.
                > trả về tmpId.
              * Reconcile khi server trả về
                > _reconcileCreated(createdRaw, tmpId):
                  = lấy real newId, merge data, xóa flags pending/temp.
                  = thay tmpId → newId trong commentsById, topLevel, repliesByParent, page cache.
                  = replay queued actions _replayQueuedActions(tmpId, newId).
                  = cleanup các map: _undoMap, _clientTmpIdToTmpId, _processedClientTmpIds.
              * Rollback khi lỗi:
                > _rollbackOptimisticCreate(tmpId): xóa tmpId khỏi commentsById, phục hồi vị trí bằng _undoMap, cập nhật child_count, page cache, cleanup maps.
            3. Action Queue (xử lý actions trên pending records):
              * Data structure: Map<tmpId, Array<Action>>
              * Action = {type: 'write'|'unlink'|'delete'|'call'|'create_child', payload, ts}
              * _enqueueAction(tmpId, action) — add + set TTL cleanup (2 phút).
              * _replayQueuedActions(tmpId, realId) — thực thi theo thứ tự:
                > write → orm.write(realId, {content:...})
                > unlink/delete → orm.unlink(realId)
                > call → gọi method (ví dụ action_toggle_like)
                > create_child → tạo reply
              * Use-case: người dùng edit/like/delete trước khi server confirm create.
            4. Page Cache:
              * pageCache: Map<pageNum, CacheMeta> 
                > CacheMeta = {ts, ids:[], comments: {id:...}, hasMore}
              * TTL = 30s (_pageCacheTTL)
              * Methods: _cacheSet, _cacheGet (return null nếu expired), _clearPageCache, _replaceTmpInCache(tmpId, newId), _removeIdFromCacheMeta(id).
              * Cache invalidation: tạo comment → invalidate page0; delete → remove from all pages; sort change → resort in-place.
            5. Sorting:
              * Sort modes:
                > like (default): like_count DESC, create_date DESC
                > date_desc: create_date DESC, like_count DESC
                > date_asc: create_date ASC, like_count DESC
              * Implement bằng pure functions: _sortByLike(ids), _sortByDateLatest(ids), _sortByDateOldest(ids) (stable sort).
              * setSortMode(mode) → cập nhật state.sortMode, resort topLevel, cached pages, repliesByParent.
              * Debounced re-sort khi like thay đổi: _maybeResortVisibleList(ids, idChanged, debounceMs=2000).
            6. Bus notifications (real-time):
              * Channel: realty_comment_{res_model}_{res_id}; subscribe in onWillStart(), unsubscribe in onWillUnmount().
              * Deduplication:
                > track _processedClientTmpIds set và _clientTmpIdToTmpId map; TTL 5s.
                > nếu payload có client_tmp_id và có mapping → gọi _reconcileCreated.
              * Handled message types:
                > "create": nếu own create → reconcile; else _handleServerPushNew.
                > "parent_update": cập nhật child_count.
                > "update": _onCommentUpdated() merge.
                > "delete": _onCommentDeleted(id, parentId).
                > "absolute_delete": set state.absoluteDelete = true, đóng dialog, disable UI.
                > "like_toggle": cập nhật like_count, trigger debounced resort.
              * _handleServerPushNew(srv): add to commentsById, repliesByParent hoặc topLevel, insert vào page cache.
            7. Pagination & Replies:
              * Top-level pages
                > loadPage(page, {force=false}):
                  = nếu cache valid và !force → return cached.
                  = gọi get_top_level_page().
                  = nếu page rỗng → fallback retry previous pages xuống tới 0.
                  = merge comments → update topLevel, sort, cache, update maxPage.
                > loadNextPage() / loadPrevPage() guard hasMore / page>0.
              * Replies
                > loadRepliesFor(parentId, page=0, limit=5):
                > prevent concurrent via repliesMeta[parentId].loading.
                > gọi get_replies_page(parentId, limit, offset).
                > Merge:
                  = serverIds = response
                  = busOnlyIds = local optimistic replies
                  = page 0: [...serverIds, ...busOnlyIds]
                  = else: append serverIds
                > update commentsById, repliesByParent[parentId], repliesMeta, showRepliesByParent[parentId]=true, repliesLoadedFromServer[parentId]=true.
              * toggleRepliesFor(parentId):
                > nếu đã visible → hide; else if not repliesLoadedFromServer → load from server (even khi có bus items); else just show.
              * loadMoreRepliesFor(parentId) → next page.
            8. Excessive Nesting Mode:
              * Trigger: level === 4 && child_count > 0.
              * enterExcessiveMode(parentId):
                > lưu excessivePrevPage, excessivePrevTopLevel.
                > set excessiveMode = true, excessiveParentId = parentId, topLevel = [parentId], page=0, hasMore=false.
                > loadRepliesFor(parentId,0,10), showRepliesByParent[parentId]=true.
                > UI: ẩn pager, show "Go back".
              * exitExcessiveMode() restore state.
            9. Top-level create & Reply flow:
              * createTopLevelComment():
                > guard absoluteDelete.
                > validate via _contentValidation(content,'create') → _sanitizeContent.
                > client_tmp_id = _makeTmpId(); tmpId = _optimisticInsert(payload, client_tmp_id).
                > dedupe: _clientTmpIdToTmpId.set(client_tmp_id, tmpId); _processedClientTmpIds.add(client_tmp_id).
                > clear input, call orm.create('realty_comment', [payload], {context: {client_tmp_id, create_or_reply: 'create'|'reply'}}).
                > success → _reconcileCreated(createdRaw, tmpId). error → _rollbackOptimisticCreate(tmpId).
            10. Editing / Like / Delete (frontend):
              * Like:
                > pending record → enqueue call action action_toggle_like, optimistic increment UI, skip server call.
                > normal record → call orm.call('realty_comment','action_toggle_like',[id]), update UI with result.
                > throttle per comment 500ms.
              * Edit:
                > validate _validationRules, throttle 1000ms.
                > pending → enqueue write, optimistic UI update.
                > normal → orm.write('realty_comment',[id],{content}).
              * Delete:
                > owner: confirm dialog → pending: remove optimistic + enqueue cancel_create; normal: orm.unlink.
                > moderator: open notify_wizard popup (context default_*), wizard calls unlink(reason) on backend → backend sends removal notification to author.
            11. Backend workflow:
              * create(vals_list):
                > require client_tmp_id & create_or_reply in context.
                > _sanitize_content(), _check_content(), _check_target_exists().
                > super().create(vals_list).
                > update parent model comment_count (compute_comment_count).
                > push bus: type "create" for top-level or "parent_update" for reply (payload normalized _normalize_for_bus()).
              * write():
                > only allow update content (or skip custom logic if context "skip_custom_realty_write_logic" for like toggle).
                > validate target, sanitize, push bus "update".
              * unlink():
                > owner delete vs moderator delete (moderator requires reason).
                > validate target exists.
                > push bus "delete" (or "parent_update" for replies).
                > if moderator delete → _send_removal_notification() (post to chatter + mail.notification).
                > allow bulk skip logic for absolute delete (post deleted) → push "absolute_delete".
              * action_toggle_like():
                > check permission via permission_tracker.
                > write with context skip; push bus "like_toggle".
            12. Sanitization & Validation (backend)
              * _sanitize_content():
                > html.escape() + Unicode category-based allowlist: Letters (L*), Numbers (N*), punctuation (Pc,Pd,Po,Ps,Pe,Sm,Sc,Sk,So), allow emojis (So), block > > > control chars (Cc), private use (Co).
                > collapse whitespace \s+ → single space, trim.
                > multilingual OK (VN, CN, AR, emojis).
              * _check_content():
                > not empty, ≤ 500 chars, not contain reserved words (from policy model).
              * _check_target_exists(), _check_parent_same_target().
            13. Security & Performance
              * XSS: backend html.escape, frontend _sanitizeContent, OWL templates use t-esc.
              * SQL injection: luôn dùng ORM.
              * Access control: record rules + permission_tracker groups.
              * Indexes: realty_comment_res_model_res_id_idx, unique comment_like_rel_unique_idx.
              * Rate limits đề xuất trên infra; client-side throttle/debounce: likes 500ms, edits 1000ms, actionQueue TTL 2min, pageCache TTL 30s.
              * Error handling: rollback on failure, graceful fallback loading reserved words empty set nếu call thất bại.