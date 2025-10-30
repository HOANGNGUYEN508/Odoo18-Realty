import {
	Component,
	useState,
	onWillStart,
	onWillUnmount,
	useRef,
} from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { RealtyCommentItem } from "./realty_comment_item";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

export class RealtyCommentDialog extends Component {
	static template = "realty_bds.comment_dialog";
	static components = { RealtyCommentItem, Dialog };
	static props = {
		params: { type: Object, optional: false },
		close: { type: Function, optional: true },
	};

	setup() {
		this.orm = useService("orm");
		this.busService = useService("bus_service");
		this.notification = useService("notification");

		const p = this.props.params || {};
		const { res_model: resModel = null, res_id } = p;
		const numericResId = res_id != null ? Number(res_id) : null;

		this.commentRef = useRef("commentInput");
		this.pageAnchorRef = useRef("pageAnchor");
		this.jumpInputRef = useRef("jumpInput");

		this.state = useState({
			commentsById: {},
			topLevel: [],
			page: 0,
			hasMore: true,
			loading: false,
			replyingTo: null,
			highlightedComment: null,
			repliesByParent: {},
			repliesMeta: {},
			showRepliesByParent: {},
			editingId: null,
			maxPage: 1,
			jumpDialog: { visible: false, input: "", style: "", error: null },
			sortMode: "like",
		});

		// internal maps / counters / caches
		this._processedClientTmpIds = new Set();
		this._tmpIdToRealId = new Map();
		this._clientTmpIdToTmpId = new Map();
		this._tmpCounter = 0;

		this._pageCache = new Map();
		this._pageCacheTTL = 30 * 1000;

		this._undoMap = new Map();

		this._actionQueue = new Map();
		this._actionQueueTTL = 2 * 60 * 1000;
		this._queueTimers = new Map();

		let channel = null;
		this._boundBusHandler = this._onBusNotification.bind(this);

		onWillStart(async () => {
			const reservedWords = await this._fetchReservedWords();

			const hasGroup = (g) => !!(g && user.hasGroup(g));
			const userSimple = Object.freeze({
				id: user.id ?? null,
				name: user.name ?? null,
				isUser:
					hasGroup(p.group?.user_group) || hasGroup(p.group?.realty_group),
				isModerator:
					hasGroup(p.group?.moderator_group) || hasGroup(p.group?.realty_group),
			});

			const ctxProps = {
				user: userSimple,
				resModel,
				resId: numericResId,
				reservedWords,
			};
			
			this.ctx = {};

			Object.defineProperties(
				this.ctx,
				Object.fromEntries(
					Object.entries(ctxProps).map(([k, v]) => [
						k,
						{
							value: v,
							writable: false,
							configurable: false,
							enumerable: true,
						},
					])
				)
			);

			channel = `realty_comment_${this.ctx.resModel}_${this.ctx.resId}`;
			this.busService.addChannel(channel);
			this.busService.subscribe("realty_notify", this._boundBusHandler);

			if (this.ctx.resModel && this.ctx.resId) {
				await this.busService.start();
				await this.loadPage(0);
			}
		});
		onWillUnmount(() => {
			if (channel) {
				this.busService.unsubscribe("realty_notify", this._boundBusHandler);
				this.busService.deleteChannel(channel);
			}
		});
	}

	// ---------- Helpers & handlers ----------
	_fetchReservedWords = async () => {
		let reservedWords = [];
		try {
			const result = await this.orm.call("policy", "get_reserved_words");
			reservedWords = Array.isArray(result) ? result.map(String) : [];
		} catch (e) {
			console.warn(
				"Failed to load reserved words from policy.get_reserved_words:",
				e
			);
			reservedWords = [];
		}
		return reservedWords;
	};

	// compute bubble style and tail offset for the anchor element
	_getBubbleStyleForAnchor = (anchorEl) => {
		if (!anchorEl || typeof anchorEl.getBoundingClientRect !== "function") {
			return "position:fixed; left:20px; top:80px; z-index:1060;";
		}
		const rect = anchorEl.getBoundingClientRect();
		const anchorCenterX = rect.left + rect.width / 2 + (window.scrollX || 0);

		const viewportPadding = 12;
		const maxWidth = Math.min(420, window.innerWidth - viewportPadding * 2);
		// place bubble left near anchor but clamp inside viewport
		let bubbleLeft = Math.max(
			viewportPadding,
			Math.min(
				rect.left + (window.scrollX || 0),
				window.innerWidth - viewportPadding - maxWidth
			)
		);
		const bubbleTop = Math.round(rect.bottom + (window.scrollY || 0) + 8);

		let tailLeft = Math.round(anchorCenterX - bubbleLeft);
		const tailMin = 12;
		const tailMax = Math.round(maxWidth - 12);
		if (tailLeft < tailMin) tailLeft = tailMin;
		if (tailLeft > tailMax) tailLeft = tailMax;

		return `position:fixed; left:${bubbleLeft}px; top:${bubbleTop}px; z-index:1060; width:auto; max-width:${maxWidth}px; --jump-tail-left:${tailLeft}px;`;
	};

	openJumpDialog = (ev) => {
		const maxP = Number(this.state.maxPage) || 1;
		if (maxP <= 4) {
			// disabled when <= 4 pages; early exit (could add a tiny flash here)
			return;
		}

		const anchor = this.pageAnchorRef && this.pageAnchorRef.el;
		const style = this._getBubbleStyleForAnchor(anchor);
		this.state.jumpDialog = {
			visible: true,
			input: String(this.state.page + 1),
			style,
			error: null,
		};

		// focus input after render
		requestAnimationFrame(() => {
			try {
				const inp = this.jumpInputRef && this.jumpInputRef.el;
				if (inp && typeof inp.focus === "function") {
					inp.focus();
					if (typeof inp.select === "function") inp.select();
				}
			} catch (e) {}
		});

		if (ev && typeof ev.stopPropagation === "function") ev.stopPropagation();
	};

	closeJumpDialog = () => {
		this.state.jumpDialog = {
			visible: false,
			input: "",
			style: "",
			error: null,
		};
	};

	onJumpKeydown = (ev) => {
		if (ev.key === "Enter") {
			ev.preventDefault();
			this.confirmJump();
		} else if (ev.key === "Escape") {
			ev.preventDefault();
			this.closeJumpDialog();
		}
	};

	confirmJump = async () => {
		const valRaw = (this.state.jumpDialog && this.state.jumpDialog.input) || "";
		const parsed = Number(valRaw);
		const maxP = Number(this.state.maxPage) || 1;

		if (!valRaw || Number.isNaN(parsed) || !Number.isInteger(parsed)) {
			this.state.jumpDialog = {
				...this.state.jumpDialog,
				error: "Please enter a whole number.",
			};
			return;
		}
		if (parsed < 1 || parsed > maxP) {
			this.state.jumpDialog = {
				...this.state.jumpDialog,
				error: `Please enter a number between 1 and ${maxP}.`,
			};
			return;
		}

		const pageToLoad = parsed - 1;
		this.closeJumpDialog();
		try {
			await this.loadPage(pageToLoad, { force: true });
			// scroll list into view
			requestAnimationFrame(() => {
				const scrollEl = document.querySelector(".o_comment_scroll");
				if (scrollEl && typeof scrollEl.scrollIntoView === "function") {
					scrollEl.scrollIntoView({ behavior: "smooth", block: "start" });
				}
			});
		} catch (e) {
			console.error("[comment-dialog] failed to jump to page", e);
			// reopen bubble with error (reuse previous style)
			this.state.jumpDialog = {
				visible: true,
				input: String(parsed),
				style: this.state.jumpDialog.style,
				error: "Failed to load page. Try again.",
			};
		}
	};

	_makeTmpId = () => {
		this._tmpCounter += 1;
		return -(Date.now() * 1000 + this._tmpCounter);
	};

	// helper: parse timestamp for a comment id (0 fallback)
	_getTimeForId = (id) => {
		const rec = this.state.commentsById?.[id] || {};
		const d = rec.create_date ? Date.parse(rec.create_date) : NaN;
		return isNaN(d) ? 0 : d;
	};

	// sort: date newest -> oldest, tie-breaker: like_count desc
	_sortByDateLatest = (ids = []) => {
		return ids.slice().sort((a, b) => {
			const ta = this._getTimeForId(a);
			const tb = this._getTimeForId(b);
			if (tb !== ta) return tb - ta; // newer first
			// tie-breaker: likes desc
			const la = Number(this.state.commentsById?.[a]?.like_count) || 0;
			const lb = Number(this.state.commentsById?.[b]?.like_count) || 0;
			if (lb !== la) return lb - la;
			// final stable tie-breaker by id descending (newer ids first)
			return Number(b) - Number(a);
		});
	};

	// sort: date oldest -> newest, tie-breaker: like_count desc
	_sortByDateOldest = (ids = []) => {
		return ids.slice().sort((a, b) => {
			const ta = this._getTimeForId(a);
			const tb = this._getTimeForId(b);
			if (ta !== tb) return ta - tb; // older first
			// tie-breaker: likes desc
			const la = Number(this.state.commentsById?.[a]?.like_count) || 0;
			const lb = Number(this.state.commentsById?.[b]?.like_count) || 0;
			if (lb !== la) return lb - la;
			// stable tie-breaker by id asc (smaller id first)
			return Number(a) - Number(b);
		});
	};

	// sort: like_count desc, tie-breaker: date newest desc
	_sortByLike = (ids = []) => {
		// sort by like_count DESC, then by create_date DESC (newest first)
		return ids.slice().sort((a, b) => {
			const aRec = this.state.commentsById?.[a] || {};
			const bRec = this.state.commentsById?.[b] || {};
			const la = Number(aRec.like_count) || 0;
			const lb = Number(bRec.like_count) || 0;
			if (lb !== la) {
				return lb - la; // higher likes first
			}

			const ta = this._getTimeForId(a);
			const tb = this._getTimeForId(b);
			// tie-breaker: newest first -> later timestamp should come first
			return tb - ta;
		});
	};

	// mode-aware sorter: picks comparator based on current state.sortMode
	_sortByMode = (ids = []) => {
		const mode = this.state?.sortMode || "like";
		switch (mode) {
			case "date_desc":
				return this._sortByDateLatest(ids);
			case "date_asc":
				return this._sortByDateOldest(ids);
			case "like":
			default:
				return this._sortByLike(ids);
		}
	};

	// expose setter for select change
	setSortMode = (mode) => {
		const allowed = new Set(["like", "date_desc", "date_asc"]);
		if (!allowed.has(mode)) mode = "like";
		// update state
		this.state.sortMode = mode;

		// reorder visible topLevel
		this.state.topLevel = this._sortByMode(this.state.topLevel);

		// update cache metas to keep consistency
		for (const [page, meta] of this._pageCache.entries()) {
			if (meta && Array.isArray(meta.ids)) {
				meta.ids = this._sortByMode(meta.ids);
				this._pageCache.set(page, meta);
			}
		}

		// reorder replies lists too
		for (const pidStr of Object.keys(this.state.repliesByParent || {})) {
			const pid = Number(pidStr);
			const list = this.state.repliesByParent[pid] || [];
			this.state.repliesByParent = {
				...this.state.repliesByParent,
				[pid]: this._sortByMode(list),
			};
		}
	};

	// shallow compare arrays
	_arraysEqual = (a = [], b = []) =>
		a.length === b.length && a.every((v, i) => b[i] === v);

	// call this to reorder a visible list (ids array) with safeguards
	_maybeResortVisibleList = (ids = [], idChanged = null, debounceMs = 2000) => {
		// update the comment map must already be applied before calling this
		// we debounce to collapse bursts
		if (!this._resortTimer) this._resortTimer = new Map();

		const key =
			ids === this.state.topLevel ? "top" : `replies_${idChanged || ""}`;
		if (this._resortTimer.has(key)) clearTimeout(this._resortTimer.get(key));

		const t = setTimeout(() => {
			this._resortTimer.delete(key);

			// compute new ordering from current commentsById
			const newOrder = this._sortByMode(ids);

			// only apply if order changed (or idMoved across page boundary if you prefer)
			if (!this._arraysEqual(newOrder, ids)) {
				// replace appropriate state (topLevel or repliesByParent)
				if (ids === this.state.topLevel) {
					this.state.topLevel = newOrder;
				} else {
					// caller must handle repliesByParent separately; this is just a helper example
				}

				// update cache meta for pages that include these ids (optional)
				for (const [page, meta] of this._pageCache.entries()) {
					if (meta.ids && meta.ids.some((x) => ids.includes(x))) {
						meta.ids = this._sortByMode(meta.ids);
						this._pageCache.set(page, meta);
					}
				}
			}
		}, debounceMs);

		this._resortTimer.set(key, t);
	};

	_replaceIdInList = (list = [], tmpId, newId) =>
		list.map((id) => (id === tmpId ? newId : id));

	// Page cache helpers
	_isCacheValid = (meta) => meta && Date.now() - meta.ts < this._pageCacheTTL;

	_cacheSet = (page, ids, comments, hasMore) => {
		this._pageCache.set(page, {
			ts: Date.now(),
			ids: ids.slice(),
			comments: { ...(comments || {}) },
			hasMore: !!hasMore,
		});
	};

	_cacheGet = (page) => {
		const meta = this._pageCache.get(page);
		if (!this._isCacheValid(meta)) return null;
		return meta;
	};

	_clearPageCache = () => {
		this._pageCache.clear();
	};

	_replaceTmpInCache = (tmpId, newId) => {
		for (const [page, meta] of this._pageCache.entries()) {
			if (!meta.ids) continue;
			let changed = false;
			meta.ids = meta.ids.map((id) => {
				if (id === tmpId) {
					changed = true;
					return newId;
				}
				return id;
			});
			if (changed) {
				// move comment record from tmp to new id in meta.comments
				const comments = { ...(meta.comments || {}) };
				if (comments[tmpId]) {
					comments[newId] = { ...comments[tmpId], id: newId };
					delete comments[tmpId];
				}
				this._pageCache.set(page, { ...meta, comments });
			}
		}
	};

	_removeIdFromCacheMeta = (id) => {
		for (const [page, meta] of this._pageCache.entries()) {
			if (!meta.ids) continue;
			if (meta.ids.includes(id)) {
				meta.ids = meta.ids.filter((x) => x !== id);
				if (meta.comments && meta.comments[id]) delete meta.comments[id];
				if (meta.ids.length === 0) {
					this._pageCache.delete(page);
				} else {
					this._pageCache.set(page, meta);
				}
			}
		}
	};

	_addOrUpdateCachedComment = (rec) => {
		if (!rec || !rec.id) return;
		this.state.commentsById = {
			...this.state.commentsById,
			[rec.id]: { ...(this.state.commentsById[rec.id] || {}), ...rec },
		};

		for (const [page, meta] of this._pageCache.entries()) {
			if (meta.ids && meta.ids.includes(rec.id)) {
				meta.comments = {
					...(meta.comments || {}),
					[rec.id]: this.state.commentsById[rec.id],
				};
				this._pageCache.set(page, meta);
			}
		}
	};

	_insertToPageCache = (rec) => {
		if (!rec || !rec.id) return;
		// update state
		this.state.commentsById = { ...this.state.commentsById, [rec.id]: rec };
		this.state.topLevel = this._sortByMode([
			...(this.state.topLevel || []),
			rec.id,
		]);

		const meta = this._pageCache.get(0);
		if (meta) {
			meta.ids = this._sortByMode([...(meta.ids || []), rec.id]);
			meta.comments = { ...(meta.comments || {}), [rec.id]: rec };
			this._pageCache.set(0, meta);
		}
	};

	// Enqueue an action for a tmpId. Actions will be replayed on reconcile.
	// action object shape (examples):
	// { type: 'write', payload: { content: 'new text' } }
	// { type: 'unlink', payload: { parentId: 123 } }
	// { type: 'call', payload: { method: 'action_toggle_like', args: [], kwargs: {} } }
	// { type: 'create_child', payload: { payload: { content, res_model, res_id, parent_id }, context: { client_tmp_id }, tmpChildId } }
	_enqueueAction = (tmpId, action) => {
		if (!tmpId || !action) return false;
		if (!this._actionQueue.has(tmpId)) this._actionQueue.set(tmpId, []);
		this._actionQueue.get(tmpId).push({ ...action, ts: Date.now() });

		// refresh TTL timer
		if (this._queueTimers.has(tmpId)) {
			clearTimeout(this._queueTimers.get(tmpId));
		}
		const t = setTimeout(() => {
			this._actionQueue.delete(tmpId);
			this._queueTimers.delete(tmpId);
		}, this._actionQueueTTL);
		this._queueTimers.set(tmpId, t);
		return true;
	};

	_cancelQueuedActions = (tmpId) => {
		if (!tmpId) return;
		if (this._queueTimers.has(tmpId)) {
			clearTimeout(this._queueTimers.get(tmpId));
			this._queueTimers.delete(tmpId);
		}
		this._actionQueue.delete(tmpId);
	};

	// Replay queued actions for a given tmpId after mapping to realId
	_replayQueuedActions = async (tmpId, realId) => {
		if (!tmpId || !realId) return;
		const queue = this._actionQueue.get(tmpId);
		if (!Array.isArray(queue) || queue.length === 0) {
			// cleanup any timers
			if (this._queueTimers.has(tmpId)) {
				clearTimeout(this._queueTimers.get(tmpId));
				this._queueTimers.delete(tmpId);
			}
			this._actionQueue.delete(tmpId);
			return;
		}

		// Process actions sequentially — simpler and safer for ordering / cancels
		for (const act of queue) {
			try {
				switch (act.type) {
					case "write": {
						// payload contains fields to write, e.g. { content: "..." }
						await this.orm.write("realty_comment", [realId], act.payload, {});
						// optimistic local update so UI doesn't wait for a push
						this._onCommentUpdated({ id: realId, ...act.payload });
						break;
					}
					case "unlink":
					case "delete": {
						// If caller provided parentId in payload (useful for UI update)
						const res = await this.orm.unlink("realty_comment", [realId]);
						const deletedId = res && res.deleted_id ? res.deleted_id : realId;
						this._onCommentDeleted(
							deletedId,
							(act.payload && act.payload.parentId) || null
						);
						break;
					}
					case "call": {
						// generic rpc call — payload must include method, args (optional), kwargs (optional)
						const method = act.payload && act.payload.method;
						const args =
							act.payload && act.payload.args ? act.payload.args : [realId];
						const kwargs =
							act.payload && act.payload.kwargs ? act.payload.kwargs : {};
						const res = await this.orm.call(
							"realty_comment",
							method,
							args,
							kwargs
						);
						// handle common method results (e.g. like toggle)
						if (
							method === "action_toggle_like" &&
							res &&
							typeof res.count === "number"
						) {
							this._onCommentUpdated({ id: realId, like_count: res.count });
						}
						break;
					}
					case "create_child": {
						// payload.payload = child create payload; .tmpChildId optionally provided
						const createdRaw = await this.orm.create(
							"realty_comment",
							[act.payload.payload],
							{
								context: act.payload.context || {},
							}
						);
						// reconcile child tmp->real if tmpChildId present
						if (act.payload && act.payload.tmpChildId) {
							await this._reconcileCreated(createdRaw, act.payload.tmpChildId);
						} else {
							// ensure created comment is merged into state
							await this._reconcileCreated(createdRaw, null);
						}
						break;
					}
					default:
						console.warn(
							"[comment-dialog] Unknown queued action type:",
							act.type
						);
				}
			} catch (e) {
				console.error(
					"[comment-dialog] Failed replaying queued action",
					act,
					e
				);
				// Best-effort: continue with other actions; consider surfacing error to user via dialog service
			}
		}

		// cleanup after replay
		if (this._queueTimers.has(tmpId)) {
			clearTimeout(this._queueTimers.get(tmpId));
			this._queueTimers.delete(tmpId);
		}
		this._actionQueue.delete(tmpId);
	};

	_onCommentUpdated = (updated) => {
		if (!updated || !updated.id) return;
		this.state.commentsById[updated.id] = {
			...this.state.commentsById[updated.id],
			...updated,
		};
		// update cache entries
		this._addOrUpdateCachedComment(updated);
	};

	_onCommentDeleted = (id, parentId = null) => {
		if (!id) return;

		try {
			const deletedIdNum = Number(id);

			// If user was replying to the deleted comment, cancel reply UI
			if (
				this.state.replyingTo !== null &&
				Number(this.state.replyingTo) === deletedIdNum
			) {
				// cancelReply clears replyingTo and highlightedComment
				this.cancelReply();
			}

			// If highlightedComment itself points to the deleted comment, clear it
			const highlightedId =
				this.state.highlightedComment && this.state.highlightedComment.id;
			if (highlightedId && Number(highlightedId) === deletedIdNum) {
				this.state.highlightedComment = null;
			}

			// If we're editing the deleted comment, cancel editing
			if (
				this.state.editingId !== null &&
				Number(this.state.editingId) === deletedIdNum
			) {
				this.cancelEditing();
			}
		} catch (e) {
			// ignore coercion errors and continue with deletion logic
			console.warn("[comment-dialog] cleanup during delete failed:", e);
		}

		// remove from comments map
		const map = { ...this.state.commentsById };
		delete map[id];
		this.state.commentsById = map;

		// If parentId provided -> remove from replies list and update parent meta
		if (parentId) {
			const pid = Number(parentId);
			const cur = this.state.repliesByParent[pid] || [];
			const updatedReplies = cur.filter((rid) => rid !== id);

			this.state.repliesByParent = {
				...this.state.repliesByParent,
				[pid]: updatedReplies,
			};

			// If replies become empty, hide replies and reset basic meta
			if (updatedReplies.length === 0) {
				this.state.showRepliesByParent = {
					...this.state.showRepliesByParent,
					[pid]: false,
				};
				this.state.repliesMeta = {
					...this.state.repliesMeta,
					[pid]: {
						...(this.state.repliesMeta[pid] || {}),
						page: 0,
						hasMore: false,
						loading: false,
					},
				};
			}

			const prevParent = this.state.commentsById[pid] || {};
			const newChildCount = Math.max((prevParent.child_count || 1) - 1, 0);
			this.state.commentsById = {
				...this.state.commentsById,
				[pid]: { ...prevParent, child_count: newChildCount },
			};

			// remove id from page cache meta if present
			this._removeIdFromCacheMeta(id);

			return;
		}

		// Top-level removal
		this.state.topLevel = (this.state.topLevel || []).filter(
			(tid) => tid !== id
		);

		// keep cache in sync
		this._removeIdFromCacheMeta(id);

		// If current page becomes empty and we are not on first page -> load previous page
		if ((this.state.topLevel || []).length === 0 && this.state.page > 0) {
			// Fire-and-forget previous page load to avoid blocking UI
			this.loadPage(Math.max(0, this.state.page - 1)).catch((e) =>
				console.error("Failed to load previous page after delete:", e)
			);
			return;
		}
	};

	_handleServerPushNew = (srv) => {
		if (!srv || !srv.id) return;
		if (this.state.commentsById[srv.id]) {
			this._onCommentUpdated(srv);
		} else {
			this.state.commentsById = { ...this.state.commentsById, [srv.id]: srv };
			if (srv.parent_id) {
				const pid = Number(srv.parent_id);
				const cur = this.state.repliesByParent[pid] || [];
				if (!cur.includes(srv.id)) {
					this.state.repliesByParent = {
						...this.state.repliesByParent,
						[pid]: this._sortByMode([srv.id, ...cur]),
					};
				}
			} else {
				if (!this.state.topLevel.includes(srv.id)) {
					this.state.topLevel = this._sortByMode([
						...(this.state.topLevel || []),
						srv.id,
					]);
				}
				// update page0 cache conservatively
				this._insertToPageCache(srv);
			}
			// ensure cache entries have the comment
			this._addOrUpdateCachedComment(srv);
		}
	};

	_onBusNotification = (payload, { id } = {}) => {
		try {
			console.log("[comment-dialog] Bus notification received:", payload, id);
			if (!payload) {
				console.warn("Empty payload received");
				return;
			}

			// If this payload carries a client_tmp_id that we mapped when creating optimistically,
			// reconcile immediately and avoid duplicate insertion.
			if (
				payload.client_tmp_id &&
				this._clientTmpIdToTmpId &&
				this._clientTmpIdToTmpId.has(payload.client_tmp_id)
			) {
				const tmpId = this._clientTmpIdToTmpId.get(payload.client_tmp_id);
				if (payload.type === "create" && payload.id) {
					// server created the real record — reconcile the optimistic tmp record
					this._reconcileCreated({ id: payload.id }, tmpId);
					// mark processed for a short window
					this._processedClientTmpIds.add(payload.client_tmp_id);
					setTimeout(
						() => this._processedClientTmpIds.delete(payload.client_tmp_id),
						5000
					);
					return;
				}
				// for other types, still mark processed to reduce duplicate work
				this._processedClientTmpIds.add(payload.client_tmp_id);
				setTimeout(
					() => this._processedClientTmpIds.delete(payload.client_tmp_id),
					5000
				);
			}

			// If we've previously processed this client_tmp_id, ignore the push
			if (
				payload.client_tmp_id &&
				this._processedClientTmpIds.has(payload.client_tmp_id)
			) {
				return;
			}

			// Handle based on type
			switch (payload.type) {
				case "create":
					this._handleServerPushNew(payload);
					break;
				case "parent_update": {
					const pid = Number(payload.id);
					if (pid && !Number.isNaN(pid)) {
						const prev = this.state.commentsById[pid] || {};
						this.state.commentsById = {
							...this.state.commentsById,
							[pid]: { ...prev, child_count: payload.child_count || 0 },
						};
					}
					break;
				}
				case "update":
					if (payload.id) this._onCommentUpdated(payload);
					break;
				case "delete":
					if (payload.id) {
						this._onCommentDeleted(payload.id, payload.parent_id);
					}
					break;
				case "like_toggle": {
					if (payload.id) {
						const id = Number(payload.id);

						// 1) update comment map first
						const prev = this.state.commentsById[id] || {};
						this.state.commentsById = {
							...this.state.commentsById,
							[id]: { ...prev, like_count: payload.like_count || 0 },
						};

						// 2) keep cached comment entry up-to-date
						this._addOrUpdateCachedComment(this.state.commentsById[id]);

						// 3) Only re-sort visible lists (debounced & only if ordering changes).
						// Top-level page visible?
						if ((this.state.topLevel || []).includes(id)) {
							// pass current topLevel snapshot; helper will re-read state when firing
							this._maybeResortVisibleList(this.state.topLevel, id);
						}

						// Replies visible for parent?
						if (payload.parent_id) {
							const pid = Number(payload.parent_id);
							if (
								Array.isArray(this.state.repliesByParent[pid]) &&
								this.state.showRepliesByParent[pid]
							)
								this._maybeResortVisibleList(
									this.state.repliesByParent[pid],
									id
								);
						}

						// (No global full re-sort; list order will update only when necessary)
					}
					break;
				}

				default:
					console.error("Unknown message type:", payload.type, payload);
			}
		} catch (e) {
			console.error("Error handling bus notification:", e, { payload, id });
		}
	};

	// ---------- Methods that interact with services / state ----------
	loadRepliesFor = async (parentId, page = 0, limit = 5) => {
		if (!parentId) return;
		const pid = Number(parentId);
		const meta = this.state.repliesMeta[pid] || {
			loading: false,
			page: 0,
			hasMore: false,
		};
		if (meta.loading) return;
		this.state.repliesMeta = {
			...this.state.repliesMeta,
			[pid]: { ...(meta || {}), loading: true },
		};

		try {
			const result = await this.orm.call(
				"realty_comment",
				"get_replies_page",
				[pid, limit, page * limit],
				{}
			);

			const nextMap = { ...this.state.commentsById };
			const ids = Array.isArray(result.replies)
				? result.replies.map((r) => {
						nextMap[r.id] = {
							id: r.id,
							content: r.content,
							create_uid: r.create_uid,
							like_count: r.like_count || 0,
							child_count: r.child_count || 0,
							res_model: r.res_model,
							res_id: r.res_id,
							create_date: r.create_date,
							parent_id: r.parent_id,
						};
						return r.id;
				  })
				: [];

			const current = this.state.repliesByParent[pid] || [];
			const newList = page === 0 ? ids : [...current, ...ids];

			this.state.commentsById = nextMap;
			this.state.repliesByParent = {
				...this.state.repliesByParent,
				[pid]: this._sortByMode(newList),
			};
			this.state.repliesMeta = {
				...this.state.repliesMeta,
				[pid]: { page, hasMore: !!result.hasMore, loading: false },
			};
			this.state.showRepliesByParent = {
				...this.state.showRepliesByParent,
				[pid]: true,
			};
		} catch (e) {
			console.error("Failed to load replies for", pid, e);
			this.state.repliesMeta = {
				...this.state.repliesMeta,
				[pid]: { ...(this.state.repliesMeta[pid] || {}), loading: false },
			};
		}
	};

	toggleRepliesFor = async (parentId) => {
		if (!parentId) return;
		const pid = Number(parentId);
		const visible = !!this.state.showRepliesByParent[pid];
		if (visible) {
			this.state.showRepliesByParent = {
				...this.state.showRepliesByParent,
				[pid]: false,
			};
			return;
		}
		const loaded =
			Array.isArray(this.state.repliesByParent[pid]) &&
			this.state.repliesByParent[pid].length > 0;
		if (!loaded) {
			await this.loadRepliesFor(pid, 0);
		} else {
			this.state.showRepliesByParent = {
				...this.state.showRepliesByParent,
				[pid]: true,
			};
		}
	};

	loadMoreRepliesFor = async (parentId) => {
		if (!parentId) return;
		const pid = Number(parentId);
		const meta = this.state.repliesMeta[pid] || {
			page: 0,
			hasMore: false,
			loading: false,
		};
		if (!meta.hasMore || meta.loading) return;
		await this.loadRepliesFor(pid, meta.page + 1);
	};

	_optimisticInsert = (payload, client_tmp_id = null) => {
		const tmpId = this._makeTmpId();
		const now = new Date().toISOString();
		const optimistic = {
			id: tmpId,
			client_tmp_id: client_tmp_id,
			content: payload.content,
			create_uid: [this.ctx.user.id, this.ctx.user.name || "You"],
			like_count: 0,
			child_count: 0,
			res_model: payload.res_model,
			res_id: payload.res_id,
			create_date: now,
			parent_id: payload.parent_id || null,
			pending: true,
			temp: true,
		};

		// always ensure the comment exists in the master map
		this.state.commentsById = {
			...this.state.commentsById,
			[tmpId]: optimistic,
		};

		if (!this._actionQueue.has(tmpId)) {
			this._actionQueue.set(tmpId, []);
			// start TTL timer for the queue
			if (this._queueTimers.has(tmpId))
				clearTimeout(this._queueTimers.get(tmpId));
			const t = setTimeout(() => {
				this._actionQueue.delete(tmpId);
				this._queueTimers.delete(tmpId);
			}, this._actionQueueTTL);
			this._queueTimers.set(tmpId, t);
		}

		// Replies branch
		if (optimistic.parent_id) {
			const pid = Number(optimistic.parent_id);
			const prev = this.state.repliesByParent[pid] || [];
			this.state.repliesByParent = {
				...this.state.repliesByParent,
				[pid]: [tmpId, ...prev],
			};
			this.state.showRepliesByParent = {
				...this.state.showRepliesByParent,
				[pid]: true,
			};
			// record undo info
			this._undoMap.set(tmpId, {
				tmpId,
				client_tmp_id,
				parentId: pid,
				insertedInto: "replies",
				prevParentChildCount:
					(this.state.commentsById[pid] &&
						this.state.commentsById[pid].child_count) ||
					0,
			});
			return tmpId;
		}

		// Top-level branch
		const PAGE_LIMIT = 10; // must match loadPage() limit
		const page0 = this._pageCache.get(0);

		// If we are on page 0 and page0 exists and is full, push optimistic into last page cache instead
		if (
			this.state.page === 0 &&
			page0 &&
			Array.isArray(page0.ids) &&
			page0.ids.length >= PAGE_LIMIT
		) {
			// determine last page index (pick max numeric key)
			const pages = Array.from(this._pageCache.keys()).filter(
				(k) => typeof k === "number"
			);
			const lastPage = pages.length ? Math.max(...pages) : 1;
			let lastMeta = this._pageCache.get(lastPage);
			if (!lastMeta) {
				lastMeta = { ts: Date.now(), ids: [], comments: {}, hasMore: true };
			}
			lastMeta.ids = [...(lastMeta.ids || []), tmpId];
			lastMeta.comments = { ...(lastMeta.comments || {}), [tmpId]: optimistic };
			this._pageCache.set(lastPage, lastMeta);

			this._undoMap.set(tmpId, {
				tmpId,
				client_tmp_id,
				parentId: null,
				insertedInto: "page_cache",
				page: lastPage,
				prevParentChildCount: null,
			});
		} else {
			// safe to show on current page (append to visible list)
			this.state.topLevel = [...(this.state.topLevel || []), tmpId];
			this._undoMap.set(tmpId, {
				tmpId,
				client_tmp_id,
				parentId: null,
				insertedInto: "top",
				prevParentChildCount: null,
			});
			// also keep page0 cache in sync if present
			const meta0 = this._pageCache.get(0);
			if (meta0 && Array.isArray(meta0.ids)) {
				meta0.ids = [...(meta0.ids || []), tmpId];
				meta0.comments = { ...(meta0.comments || {}), [tmpId]: optimistic };
				this._pageCache.set(0, meta0);
			}
		}

		return tmpId;
	};

	_rollbackOptimisticCreate = (tmpId, markFailed = true) => {
		if (!tmpId) return;
		const undo = this._undoMap.get(tmpId);
		// remove from comments map
		const map = { ...this.state.commentsById };
		if (map[tmpId]) delete map[tmpId];
		this.state.commentsById = map;

		if (undo) {
			if (undo.insertedInto === "replies" && undo.parentId != null) {
				const pid = undo.parentId;
				this.state.repliesByParent = {
					...this.state.repliesByParent,
					[pid]: (this.state.repliesByParent[pid] || []).filter(
						(id) => id !== tmpId
					),
				};
				// restore parent child_count
				const prevParent = this.state.commentsById[pid] || {};
				this.state.commentsById = {
					...this.state.commentsById,
					[pid]: {
						...prevParent,
						child_count:
							undo.prevParentChildCount ||
							Math.max((prevParent.child_count || 1) - 1, 0),
					},
				};
			} else if (undo.insertedInto === "top") {
				this.state.topLevel = (this.state.topLevel || []).filter(
					(id) => id !== tmpId
				);
			}
			// cleanup caches
			this._removeIdFromCacheMeta(tmpId);
			this._clientTmpIdToTmpId.delete(undo.client_tmp_id);
			this._processedClientTmpIds.delete(undo.client_tmp_id);
			this._undoMap.delete(tmpId);
		} else {
			// generic cleanup
			this.state.topLevel = (this.state.topLevel || []).filter(
				(id) => id !== tmpId
			);
			this._removeIdFromCacheMeta(tmpId);
		}

		// Optionally mark a transient failed indicator in UI elsewhere. For now we removed the tmp row.
	};

	_reconcileCreated = async (createdRaw, tmpId = null) => {
		let newId = null;
		if (typeof createdRaw === "number") {
			newId = createdRaw;
		} else if (Array.isArray(createdRaw) && typeof createdRaw[0] === "number") {
			newId = createdRaw[0];
		} else if (createdRaw && createdRaw.id) {
			newId = createdRaw.id;
		} else {
			console.warn(
				"[comment-dialog] _reconcileCreated: unexpected createdRaw:",
				createdRaw
			);
			return;
		}

		if (tmpId && this.state.commentsById[tmpId]) {
			const tmpRec = this.state.commentsById[tmpId];

			const finalized = {
				...tmpRec,
				id: newId,
				pending: false,
				temp: false,
			};

			const map = { ...this.state.commentsById };
			if (map[newId]) {
				Object.assign(map[newId], finalized);
			} else {
				map[newId] = finalized;
			}
			delete map[tmpId];
			this.state.commentsById = map;

			const parentId = tmpRec.parent_id ? Number(tmpRec.parent_id) : null;
			if (parentId) {
				const current = this.state.repliesByParent[parentId] || [];
				const index = current.indexOf(tmpId);
				if (index !== -1) {
					const updated = [...current];
					updated[index] = newId;
					this.state.repliesByParent = {
						...this.state.repliesByParent,
						[parentId]: this._sortByMode(updated),
					};
				}
			} else {
				const index = this.state.topLevel.indexOf(tmpId);
				if (index !== -1) {
					const updated = [...this.state.topLevel];
					updated[index] = newId;
					this.state.topLevel = this._sortByMode(updated);
				} else {
					// Replace tmp in cache (if present) or append newId to last page.
					this._replaceTmpInCache(tmpId, newId);

					// if last page is currently visible, refresh topLevel from that page's ids
					const pages = Array.from(this._pageCache.keys());
					const lastPage = pages.length ? Math.max(...pages) : null;
					if (lastPage !== null && this.state.page === lastPage) {
						const meta = this._pageCache.get(lastPage) || { ids: [] };
						this.state.topLevel = (meta.ids || []).slice();
					}
				}
			}

			try {
				this._tmpIdToRealId.set(tmpId, newId);
				setTimeout(() => {
					this._tmpIdToRealId.delete(tmpId);
				}, 5000);
			} catch (e) {}

			// update caches: replace tmp with real id
			this._replaceTmpInCache(tmpId, newId);
			this._addOrUpdateCachedComment(this.state.commentsById[newId]);

			try {
				// ensure replay finishes (so queued writes/deletes happen right after reconcile)
				await this._replayQueuedActions(tmpId, newId);
			} catch (e) {
				console.error("[comment-dialog] replay queued actions failed:", e);
			}

			// cleanup undo map and client mappings
			const undo = this._undoMap.get(tmpId);
			if (undo) {
				this._undoMap.delete(tmpId);
				this._clientTmpIdToTmpId.delete(undo.client_tmp_id);
				this._processedClientTmpIds.delete(undo.client_tmp_id);
			}

			return;
		}

		// No tmp found locally — ensure minimal placeholder exists if missing
		if (!this.state.commentsById[newId]) {
			this.state.commentsById = {
				...this.state.commentsById,
				[newId]: {
					id: newId,
					content: "",
					create_uid: false,
					like_count: 0,
					child_count: 0,
					res_model: this.ctx.resModel,
					res_id: this.ctx.resId,
					create_date: new Date().toISOString(),
				},
			};
		}
	};

	// UI helpers used by template
	getComment = (id) => this.state.commentsById[id];

	get replyingToName() {
		return (
			this.state.highlightedComment?.create_uid?.[1] ||
			this.state.commentsById?.[this.state.replyingTo]?.create_uid?.[1] ||
			"..."
		);
	}

	// startReply handles either (ev, comment) or (comment)
	startReply = (evOrComment, maybeComment) => {
		let ev = null,
			comment = null;
		if (maybeComment === undefined) {
			comment = evOrComment;
		} else {
			ev = evOrComment;
			comment = maybeComment;
		}
		if (ev && typeof ev.stopPropagation === "function") ev.stopPropagation();

		this.state.replyingTo = comment ? comment.id : null;
		this.state.highlightedComment = comment || null;

		requestAnimationFrame(() => {
			const el = this.commentRef.el;
			if (el && typeof el.focus === "function") {
				try {
					el.focus();
					if (typeof el.select === "function") el.select();
				} catch (e) {}
			}
		});
	};

	cancelReply = () => {
		this.state.replyingTo = null;
		this.state.highlightedComment = null;
	};

	handleKeydown = (ev) => {
		if (ev.key === "Enter") {
			ev.preventDefault();
			this.createTopLevelComment();
		}
	};

	startEditing = (id) => {
		this.state.editingId = id;
	};

	cancelEditing = () => {
		this.state.editingId = null;
	};

	_errorHandler = (e, ms) => {
		this.notification.add(`❌ Error: ${ms}`, {
			title: `${e} Error`,
			type: "danger",
		});
	};

	_validationRules = (content) => {
		const txt = (content || "").toLowerCase();
		if (!txt) {
			// empty content not allowed to foward but silently ignore since user may accidentally hit enter
			return false;
		}
		if (txt.length > 500) {
			this._errorHandler("Content", "Content must be under 500 characters.");
			return false;
		}
		if (this.ctx.reservedWords && this.ctx.reservedWords.size > 0) {
			const match = Array.from(this._reservedWords).find(
				(w) => w && txt.includes(w)
			);
			if (match) {
				this._errorHandler(
					"Content",
					`Content contains reserved word: '${match}'`
				);
				return false;
			}
		}
		return true;
	};

	_contentValidation = (content, type, comment) => {
		const txt = (content || "").toLowerCase();
		switch (type) {
			case "create": {
				if (!this.ctx.user.isUser) {
					this._errorHandler(
						"Authentication",
						`You must be a user of ${this.ctx.resModel} to post a comment.`
					);
					return false;
				}
				const result = this._validateRules(content);
				return result;
			}
			case "edit": {
				if (
					!comment ||
					!comment.create_uid ||
					comment.create_uid[0] !== this.ctx.user.id
				) {
					this._errorHandler(
						"Authentication",
						"You can only edit your own comments."
					);
					return false;
				}
				const result = this._validateRules(content);
				return result;
			}
			case "delete": {
				if (!comment) {
					this._errorHandler("Content", "Comment not found.");
					return false;
				}
				const isOwner =
					comment.create_uid && comment.create_uid[0] === this.ctx.user.id;
				const isModerator = this.ctx.user.isModerator;
				if (!isOwner && !isModerator) {
					this._errorHandler(
						"Authentication",
						"You can only delete your own comments or must be a moderator."
					);
					return false;
				}
				return true;
			}
			default:
				return false;
		}
	};

	// create comment (optimistic + reconcile)
	createTopLevelComment = async () => {
		const input = this.commentRef.el;
		const content = input?.value?.trim();

		const validation = this._contentValidation(content, "create");

		if (!validation) return;

		const client_tmp_id = this._makeTmpId(); // Generate for deduplication

		const payload = {
			content: content,
			res_model: this.ctx.resModel,
			res_id: this.ctx.resId,
		};
		if (this.state.replyingTo) {
			payload.parent_id = this.state.replyingTo;
			const parentComment = this.state.commentsById[this.state.replyingTo];
			if (parentComment) {
				if (parentComment.res_model)
					payload.res_model = parentComment.res_model;
				if (parentComment.res_id) payload.res_id = parentComment.res_id;
			}
		}

		// Insert optimistically and register the mapping for dedupe
		const tmpId = this._optimisticInsert(payload, client_tmp_id);

		try {
			this._clientTmpIdToTmpId.set(client_tmp_id, tmpId);
			this._processedClientTmpIds.add(client_tmp_id);
			setTimeout(() => {
				this._processedClientTmpIds.delete(client_tmp_id);
				this._clientTmpIdToTmpId.delete(client_tmp_id);
			}, 5000);
		} catch (e) {
			// no-op on map errors
		}

		if (input) input.value = "";
		this.cancelReply();

		try {
			const createdRaw = await this.orm.create("realty_comment", [payload], {
				context: { client_tmp_id },
			});
			await this._reconcileCreated(createdRaw, tmpId);
		} catch (e) {
			console.error("Error creating comment:", e);
			// rollback optimistic insert (server denied or erred)
			this._rollbackOptimisticCreate(tmpId);
			this._errorHandler("Roll Back", e);
		}
	};

	// ---------- pagination / top-level loading ----------
	async loadPage(page = 0, { force = false } = {}) {
		if (!this.ctx.resModel || !this.ctx.resId) return;
		if (this.state.loading) return;

		this.state.loading = true;
		try {
			const limit = 10; // must match server page size
			let tryPage = Number(page) || 0;

			// If cache available and not forced, use it
			if (!force) {
				const cached = this._cacheGet(tryPage);
				if (cached) {
					// merge cached comments to state
					this.state.commentsById = {
						...this.state.commentsById,
						...(cached.comments || {}),
					};
					this.state.topLevel = (cached.ids || []).slice();
					this.state.page = tryPage;
					this.state.hasMore = !!cached.hasMore;
					this.state.loading = false;
					return;
				}
			}

			let records = [];
			let res = null;

			// Try pages downward until we find some records or reach page 0
			while (true) {
				const offset = tryPage * limit;
				try {
					// call server-side method that returns { comments: [...], hasMore: bool, page: int }
					res = await this.orm.call(
						"realty_comment",
						"get_top_level_page",
						[this.ctx.resModel, this.ctx.resId, limit, offset],
						{}
					);
				} catch (e) {
					// server call failed for this page — if we're not at page 0, try previous page
					console.error("[comment-dialog] get_top_level_page failed:", e, {
						tryPage,
					});
					if (tryPage <= 0) {
						records = [];
						break;
					}
					tryPage = Math.max(0, tryPage - 1);
					continue;
				}

				records = Array.isArray(res && res.comments) ? res.comments : [];

				// break if we found results or we are at page 0 (to avoid infinite loop)
				if (Array.isArray(records) && records.length > 0) break;
				if (tryPage <= 0) break;
				tryPage = Math.max(0, tryPage - 1);
			}

			// Merge records into commentsById and normalize shape
			const nextMap = { ...this.state.commentsById };
			records.forEach((r) => {
				nextMap[r.id] = {
					id: r.id,
					content: r.content,
					create_uid: r.create_uid,
					create_date: r.create_date,
					like_count: r.like_count || 0,
					child_count: r.child_count || 0,
					res_model: r.res_model,
					res_id: r.res_id,
				};
			});

			this.state.commentsById = nextMap;

			const totalCount =
				res && typeof res.total_count === "number"
					? Number(res.total_count)
					: null;
			if (totalCount !== null) {
				this.state.maxPage = Math.max(1, Math.ceil(totalCount / limit));
			} else {
				this.state.maxPage = 1;
			}

			// Derive topLevel from returned records but defensively re-sort with comparator
			const ids = records.map((r) => r.id);
			this.state.topLevel = this._sortByMode(ids);
			this.state.page = tryPage;
			this.state.hasMore = !!(res && res.hasMore);

			// cache this page (store actual comment objects for quick reuse)
			this._cacheSet(
				tryPage,
				this.state.topLevel,
				Object.fromEntries(
					this.state.topLevel.map((id) => [id, this.state.commentsById[id]])
				),
				this.state.hasMore
			);
		} catch (e) {
			console.error("Failed to load comments", e);
		} finally {
			this.state.loading = false;
		}
	}

	async loadNextPage() {
		if (!this.state.hasMore || this.state.loading) return;
		await this.loadPage(this.state.page + 1);
	}

	async loadPrevPage() {
		if (this.state.page <= 0 || this.state.loading) return;
		await this.loadPage(this.state.page - 1);
	}
}
