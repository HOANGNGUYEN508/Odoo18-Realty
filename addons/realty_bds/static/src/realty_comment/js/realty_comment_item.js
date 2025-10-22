import { Component, useState, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";
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
		isModerator: { type: Boolean, optional: true },
		isUser: { type: Boolean, optional: true },
		replyingTo: { type: Number, optional: true },
		getReplies: { type: Function, optional: true }, // reads replies array from dialog
		loadReplies: { type: Function, optional: true }, // asks dialog to load replies
		loadMoreReplies: { type: Function, optional: true }, // asks dialog to load more replies
		toggleReplies: { type: Function, optional: true }, // asks dialog to toggle visibility
		getRepliesMeta: { type: Function, optional: true }, // meta (loading/hasMore/page)
		isRepliesVisible: { type: Function, optional: true }, // visibility flag
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
			this.commentData.create_uid[0] === user.userId
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
					id: this.commentData.id,
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
		this.local.editing = true;
		this.local.editingContent = this.commentData.content || "";
		setTimeout(() => {
			try {
				this.editRef.el && this.editRef.el.focus();
			} catch (e) {}
		}, 0);
	}

	cancelEdit() {
		this.local.editing = false;
		this.local.editingContent = "";
	}

	async saveEdit() {
		// Clear any pending save
		if (this._editThrottleTimeout) {
			clearTimeout(this._editThrottleTimeout);
		}

		// Throttle edit saves
		this._editThrottleTimeout = setTimeout(async () => {
			const newContent = (this.local.editingContent || "").trim();
			if (!newContent) return;

			try {
				const result = await this.orm.call(
					"realty_comment",
					"action_edit_comment",
					[this.commentData.id, newContent],
					{}
				);
				this.props.onUpdated && this.props.onUpdated(result);
				this.local.editing = false;
			} catch (e) {
				console.error("Edit failed", e);
			}
		}, 1000);
	}

	// ---------- Delete ----------
	async deleteComment() {
		this.dialogService.add(ConfirmationDialog, {
			title: "Confirm Deletion",
			body: "Are you sure you want to delete your comment?",
			confirmLabel: "Delete",
			confirm: async () => {
				try {
					const result = await this.orm.call(
						"realty_comment",
						"action_delete_comment",
						[this.commentData.id],
						{}
					);
					if (result && result.deleted_id) {
						this.props.onDeleted && this.props.onDeleted(result.deleted_id);
					}
				} catch (e) {
					console.error("Delete failed", e);
				}
			},
			cancel: () => {},
		});
	}
}
