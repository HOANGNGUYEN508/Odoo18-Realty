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

		const p = this.props.params || {};
		this.resModel = p.res_model ?? null;
		this.resId = p.res_id != null ? Number(p.res_id) : null;

		this.hasModeratorAccess = p.group?.moderator_group
			? user.hasGroup(p.group.moderator_group)
			: false;
		this.hasRealtyAccess = p.group?.realty_group
			? user.hasGroup(p.group.realty_group)
			: false;
		this.hasUserAccess = p.group?.user_group
			? user.hasGroup(p.group.user_group)
			: false;
		this.isModerator = this.hasModeratorAccess || this.hasRealtyAccess;
		this.isUser = this.hasUserAccess || this.hasRealtyAccess;

		this.commentRef = useRef("commentInput");

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
			// processedTmpIds: new Set(),
			// tmpIdToRealId: new Map(),
		});

		this._processedClientTmpIds = new Set(); // track client_tmp_id we've processed/registered
		this._tmpIdToRealId = new Map(); // tmpId -> real numeric id
		this._clientTmpIdToTmpId = new Map(); // client_tmp_id -> tmpId
		this._tmpCounter = 0;

		// register bus channel
		this._boundBusHandler = this._onBusNotification.bind(this);
		const channel = `realty_comment_${this.resModel}_${this.resId}`;
		this.busService.addChannel(channel);
		this.busService.subscribe("realty_notify", this._boundBusHandler);

		onWillStart(async () => {
			if (this.resModel && this.resId) {
				await this.busService.start();
				await this.loadPage(0);
			}
		});

		onWillUnmount(() => {
			this.busService.unsubscribe("realty_notify", this._boundBusHandler);
			this.busService.deleteChannel(channel);
		});
	}

	// ---------- Helpers & handlers ----------
	_makeTmpId = () => {
		this._tmpCounter += 1;
		return -(Date.now() * 1000 + this._tmpCounter);
	};

	_sortByDateDesc = (ids = []) => {
		return ids.slice().sort((a, b) => {
			const aRec = this.state.commentsById?.[a] || {};
			const bRec = this.state.commentsById?.[b] || {};

			// normalize like_count to integer (default 0)
			const la = Number(aRec.like_count) || 0;
			const lb = Number(bRec.like_count) || 0;
			if (lb !== la) {
				return lb - la; // higher like_count first
			}

			// normalize create_date to timestamp (default 0)
			const daRaw = aRec.create_date;
			const dbRaw = bRec.create_date;
			const da = daRaw ? Date.parse(daRaw) : 0;
			const db = dbRaw ? Date.parse(dbRaw) : 0;
			// Date.parse returns NaN for invalid dates -> treat as 0
			const ta = isNaN(da) ? 0 : da;
			const tb = isNaN(db) ? 0 : db;

			return tb - ta; // newer first
		});
	};

	_replaceIdInList = (list = [], tmpId, newId) =>
		list.map((id) => (id === tmpId ? newId : id));

	_onCommentUpdated = (updated) => {
		if (!updated || !updated.id) return;
		const prev = this.state.commentsById[updated.id] || {};
		this.state.commentsById = {
			...this.state.commentsById,
			[updated.id]: { ...prev, ...updated },
		};
	};

	_onCommentDeleted = (id) => {
		if (!id) return;
		const map = { ...this.state.commentsById };
		delete map[id];
		this.state.commentsById = map;
		this.state.topLevel = this.state.topLevel.filter((tid) => tid !== id);
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
						[pid]: this._sortByDateDesc([srv.id, ...cur]),
					};
				}
			} else {
				if (!this.state.topLevel.includes(srv.id)) {
					this.state.topLevel = this._sortByDateDesc([
						srv.id,
						...this.state.topLevel,
					]);
				}
			}
		}
	};

	_onBusNotification = (payload, { id } = {}) => {
		try {
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
						this._onCommentDeleted(payload.id);
						if (payload.parent_id) {
							const pId = Number(payload.parent_id);
							const prev = this.state.commentsById[pId] || {};
							this.state.commentsById = {
								...this.state.commentsById,
								[pId]: {
									...prev,
									child_count:
										payload.child_count ??
										Math.max((prev.child_count || 1) - 1, 0),
								},
							};
						}
					}
					break;
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
				[pid]: this._sortByDateDesc(newList),
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
			create_uid: [user.userId, user.name || "You"],
			like_count: 0,
			child_count: 0,
			res_model: payload.res_model,
			res_id: payload.res_id,
			create_date: now,
			parent_id: payload.parent_id || null,
			pending: true,
			temp: true,
		};

		// insert into state
		this.state.commentsById = {
			...this.state.commentsById,
			[tmpId]: optimistic,
		};

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
		} else {
			this.state.topLevel = [tmpId, ...this.state.topLevel];
		}

		return tmpId;
	};

	_reconcileCreated = async (createdRaw, tmpId = null) => {
		// normalize server returned id (server returns number or [number] or dict)
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

		// If we have a temporary item locally, swap it to the real id
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

			// Replace tmpId in topLevel or repliesByParent
			const parentId = tmpRec.parent_id ? Number(tmpRec.parent_id) : null;
			if (parentId) {
				const current = this.state.repliesByParent[parentId] || [];
				const index = current.indexOf(tmpId);
				if (index !== -1) {
					const updated = [...current];
					updated[index] = newId;
					this.state.repliesByParent = {
						...this.state.repliesByParent,
						[parentId]: this._sortByDateDesc(updated),
					};
				}
			} else {
				const index = this.state.topLevel.indexOf(tmpId);
				if (index !== -1) {
					const updated = [...this.state.topLevel];
					updated[index] = newId;
					this.state.topLevel = this._sortByDateDesc(updated);
				} else {
					this.state.topLevel = this._sortByDateDesc([
						newId,
						...(this.state.topLevel || []),
					]);
				}
			}

			// Track the mapping for short-term dedupe and cleanup
			try {
				this._tmpIdToRealId.set(tmpId, newId);
				setTimeout(() => {
					this._tmpIdToRealId.delete(tmpId);
				}, 5000);
			} catch (e) {}

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
					res_model: this.resModel,
					res_id: this.resId,
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

	_topLevelDomain = () => [
		["res_model", "=", this.resModel],
		["res_id", "=", this.resId],
		["comment_level", "=", 0],
	];

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

	// create comment (optimistic + reconcile)
	createTopLevelComment = async () => {
		const input = this.commentRef.el;
		const content = input?.value?.trim();
		if (!content) return;

		const client_tmp_id = this._makeTmpId(); // Generate for deduplication

		const payload = {
			content: content,
			res_model: this.resModel,
			res_id: this.resId,
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

		// register mapping and mark client_tmp_id processed immediately so early bus pushes reconcile
		try {
			this._clientTmpIdToTmpId.set(client_tmp_id, tmpId);
			this._processedClientTmpIds.add(client_tmp_id);
			// auto-cleanup after 5 seconds
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
			const map = { ...this.state.commentsById };
			if (map[tmpId])
				map[tmpId] = { ...map[tmpId], pending: false, failed: true };
			this.state.commentsById = map;
		}
	};

	// ---------- pagination / top-level loading ----------
	async loadPage(page = 0) {
		if (!this.resModel || !this.resId) return;
		if (this.state.loading) return;

		this.state.loading = true;
		try {
			const limit = 10;
			const offset = page * limit;
			const fields = [
				"id",
				"content",
				"create_uid",
				"create_date",
				"like_count",
				"child_count",
				"res_model",
				"res_id",
			];

			const records = await this.orm.call(
				"realty_comment",
				"search_read",
				[this._topLevelDomain(), fields],
				{ limit, offset, order: "create_date DESC" }
			);

			const nextMap = { ...this.state.commentsById };
			records.forEach((r) => {
				nextMap[r.id] = {
					id: r.id,
					content: r.content,
					create_uid: r.create_uid,
					like_count: r.like_count || 0,
					child_count: r.child_count || 0,
					res_model: r.res_model,
					res_id: r.res_id,
					create_date: r.create_date,
				};
			});

			this.state.commentsById = nextMap;
			this.state.topLevel = records.map((r) => r.id);
			this.state.page = page;
			this.state.hasMore = records.length === limit;
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
