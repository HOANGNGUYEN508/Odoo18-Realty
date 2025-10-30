import { Component, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class RealtyCommentItem extends Component {
	static template = "realty_bds.RealtyCommentItem";
	// allow recursion
	static components = { RealtyCommentItem };
	static props = {
		id: { type: Number, optional: true },
		comment: { type: Object, optional: true },
		getComment: { type: Function, optional: true },
		onReply: { type: Function, optional: true },
		onUpdated: { type: Function, optional: true },
		onDeleted: { type: Function, optional: true },
		level: { type: Number, optional: true },
		ctx: { type: Object, optional: true },
		replyingTo: { type: Number, optional: true },
		getReplies: { type: Function, optional: true }, // reads replies array from dialog
		loadReplies: { type: Function, optional: true }, // asks dialog to load replies
		loadMoreReplies: { type: Function, optional: true }, // asks dialog to load more replies
		toggleReplies: { type: Function, optional: true }, // asks dialog to toggle visibility
		getRepliesMeta: { type: Function, optional: true }, // meta (loading/hasMore/page)
		isRepliesVisible: { type: Function, optional: true }, // visibility flag
		onEditStart: { type: Function, optional: true }, // (id) => void
		onEditCancel: { type: Function, optional: true }, // () => void
		editingId: { type: Number, optional: true }, // id of comment being edited
		enqueueAction: { type: Function, optional: true },
		validateContent: { type: Function, optional: true },
	};

	setup() {
		this.orm = useService("orm");
		this.dialogService = useService("dialog");

		this.local = useState({
			togglingLike: false,
			editing: false,
			editingContent: "",
		});

		this.editRef = useRef("editInput");

		// Throttle like toggles (500ms)
		this._likeThrottleTimeouts = new Map();

		// Throttle edit saves (1000ms)
		this._editThrottleTimeout = null;
	}

	// always read the latest from props or parent's callback
	get commentData() {
		try {
			if (this.props.getComment && (this.props.id || this.props.id === 0)) {
				const shared = this.props.getComment(this.props.id);
				if (shared && Object.keys(shared).length) return shared;
			}
		} catch (e) {
			// ignore and fallback
		}
		return this.props.comment || {};
	}

	get isCommentAuthor() {
		return (
			this.commentData.create_uid &&
			this.commentData.create_uid[0] === this.props.ctx.user.id
		);
	}

	// compute highlight from replyingTo id and own id
	get isHighlighted() {
		const replyingTo = this.props.replyingTo ?? null;
		const data = this.commentData || {};
		const id = data.id ?? this.props.id ?? null;
		if (replyingTo == null || id == null) return false;
		try {
			return Number(replyingTo) === Number(id);
		} catch (e) {
			return replyingTo === id;
		}
	}

	// helper to detect pending/temp record
	_isPendingRec() {
		const rec = this.commentData || {};
		// consider explicit flags or negative tmp ids
		return !!(rec.temp || rec.pending || (rec.id && Number(rec.id) < 0));
	}

	startReply(ev) {
		try {
			if (ev && typeof ev.stopPropagation === "function") ev.stopPropagation();
		} catch (e) {}
		const c = this.commentData;
		this.props.onReply && this.props.onReply(ev, c);
	}

	async loadReplies(page = 0) {
		const id = this.commentData && this.commentData.id;
		if (!id) return;
		if (this.props.loadReplies) {
			await this.props.loadReplies(id, page);
		}
	}

	async loadNextReplies() {
		const id = this.commentData && this.commentData.id;
		if (!id) return;
		if (this.props.loadMoreReplies) {
			await this.props.loadMoreReplies(id);
		}
	}

	async toggleReplies() {
		const id = this.commentData && this.commentData.id;
		if (!id) return;
		if (this.props.toggleReplies) {
			await this.props.toggleReplies(id);
		}
	}

	async toggleLike() {
		const commentId = this.commentData.id;

		// Throttle check
		if (this._likeThrottleTimeouts.has(commentId)) {
			return;
		}

		// If comment is pending/temp and parent provided an enqueueAction, queue it instead
		if (this._isPendingRec()) {
			if (this.props.enqueueAction) {
				// enqueue a generic call action for toggling like
				this.props.enqueueAction(commentId, {
					type: "call",
					payload: { method: "action_toggle_like", args: [], kwargs: {} },
				});
				// optimistic local increment so UI feels responsive
				const prev = this.commentData;
				const optimisticCount = (prev.like_count || 0) + 1;
				this.props.onUpdated &&
					this.props.onUpdated({ id: commentId, like_count: optimisticCount });
				// set throttle locally to avoid multiple queued toggles quickly
				this._likeThrottleTimeouts.set(
					commentId,
					setTimeout(() => {
						this._likeThrottleTimeouts.delete(commentId);
					}, 500)
				);
			}
			return;
		}

		this.local.togglingLike = true;

		try {
			const result = await this.orm.call(
				"realty_comment",
				"action_toggle_like",
				[commentId],
				{}
			);

			if (result && typeof result.count === "number") {
				const updated = {
					id: commentId,
					like_count: result.count,
				};
				this.props.onUpdated && this.props.onUpdated(updated);
			}

			// Set throttle timeout
			this._likeThrottleTimeouts.set(
				commentId,
				setTimeout(() => {
					this._likeThrottleTimeouts.delete(commentId);
				}, 500)
			);
		} catch (e) {
			console.error("Toggle like failed", e);
			this._likeThrottleTimeouts.delete(commentId);
		} finally {
			this.local.togglingLike = false;
		}
	}

	// ---------- Editing ----------
	startEdit() {
		// set the parent's editing id if callback provided, else fallback to local editing
		const c = this.commentData;
		this.local.editingContent = c.content || "";
		if (this.props.onEditStart) {
			this.props.onEditStart(c.id);
		} else {
			this.local.editing = true;
		}
		// focus managed in parent-based flow via lifecycle or small timeout
		setTimeout(() => {
			try {
				this.editRef.el && this.editRef.el.focus();
			} catch (e) {}
		}, 0);
	}

	cancelEdit() {
		// if parent controls editing, tell parent to cancel; else use local flag
		if (this.props.onEditCancel) {
			this.props.onEditCancel();
		} else {
			this.local.editing = false;
		}
		this.local.editingContent = "";
	}

	async saveEdit() {
		const newContent = (this.local.editingContent || "").trim();
		const comment = this.commentData;

		if (this.props.validateContent) {
			const isValid = this.props.validateContent(newContent, "edit", comment);
			if (!isValid) {
				return;
			}
		}

		// Clear any pending save
		if (this._editThrottleTimeout) {
			clearTimeout(this._editThrottleTimeout);
		}

		// Throttle edit saves
		this._editThrottleTimeout = setTimeout(async () => {
			const id = comment.id;

			// If pending/temp: enqueue the write action
			if (this._isPendingRec()) {
				if (this.props.enqueueAction) {
					this.props.enqueueAction(id, {
						type: "write",
						payload: { content: newContent },
					});
					// optimistic local update
					this.props.onUpdated &&
						this.props.onUpdated({ id, content: newContent });
					this.props.onEditCancel && this.props.onEditCancel();
					this.local.editingContent = "";
				}
				return;
			}

			try {
				const result = await this.orm.write(
					"realty_comment",
					[id],
					{ content: newContent },
					{}
				);
				// update UI optimistically (server typically pushes an update anyway)
				this.props.onUpdated &&
					this.props.onUpdated({ id, content: newContent });
				this.props.onEditCancel && this.props.onEditCancel();
				this.local.editingContent = "";
			} catch (e) {
				console.error("Save edit failed", e);
			}
		}, 1000);
	}

	// ---------- Delete ----------
	async deleteComment() {
		const comment = this.commentData;
		if (this.props.validateContent) {
			const isValid = this.props.validateContent(null, "delete", comment);
			if (!isValid) return;
		}
		this.dialogService.add(ConfirmationDialog, {
			title: "Confirm Deletion",
			body: "Are you sure you want to delete your comment?",
			confirmLabel: "Delete",
			confirm: async () => {
				try {
					const id = comment.id;
					const parentId = comment.parent_id || null;

					// If pending/temp: prefer cancelling queued create (if parent provided hook)
					if (this._isPendingRec()) {
						// remove optimistic UI immediately
						this.props.onDeleted && this.props.onDeleted(id, parentId);
						// ask parent to cancel queued actions (if available)
						if (this.props.enqueueAction) {
							// we use a special action type 'cancel_create' which the parent queue handler should treat as canceling the pending create and clearing queue
							this.props.enqueueAction(id, { type: "cancel_create" });
						}
						return;
					}

					// Normal flow: call unlink on server
					const result = await this.orm.unlink("realty_comment", [id]);
					// if server returns deleted id, pass it along; otherwise fall back to id
					const deletedId =
						result && result.deleted_id ? result.deleted_id : id;
					if (deletedId) {
						const pid = parentId;
						this.props.onDeleted && this.props.onDeleted(deletedId, pid);
					}
				} catch (e) {
					console.error("Delete failed", e);
				}
			},
			cancel: () => {},
		});
	}

	get isEditing() {
		const data = this.commentData || {};
		const id = data.id ?? this.props.id ?? null;
		// if parent passes editingId, use that; else fallback to local.editing
		if (this.props.editingId !== undefined && this.props.editingId !== null) {
			try {
				return Number(this.props.editingId) === Number(id);
			} catch (e) {
				return this.props.editingId === id;
			}
		}
		return !!this.local.editing;
	}
}
