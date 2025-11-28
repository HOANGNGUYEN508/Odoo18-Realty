import { Component, useState } from "@odoo/owl";
import { IMAGE_MIMETYPES, FILE_TYPE_ICONS } from "./constants";

export class PhotoLightbox extends Component {
	static template = "realty_bds.PhotoLightbox";
	static props = {
		files: { type: Array },
		index: { type: Number },
		presentationImage: { type: Boolean },
		presentationId: { type: Number, optional: true },
		onClose: { type: Function },
		onDelete: { type: Function },
		onNavigate: { type: Function },
		onSetPresentation: { type: Function },
		readonly: { type: Boolean },
	};

	setup() {
		this.state = useState({ loading: true });
	}

	onImageLoad() {
		this.state.loading = false;
	}

	get currentFile() {
		return this.props.files.find((file) => file.id === this.props.index);
	}

	get isImage() {
		const file = this.currentFile;
		if (!file) return false;

		if (file.mimetype) {
			return IMAGE_MIMETYPES.includes(file.mimetype);
		}

		return true;
	}

	getFileIcon(mimetype) {
		return FILE_TYPE_ICONS[mimetype] || "/web/static/src/img/mimetypes/binary.svg";
	}

	get displayUrl() {
		const file = this.currentFile;
		if (!file) return null;

		if (this.isImage) {
			return file.url;
		}

		if (file.thumbnailUrl) {
			return file.thumbnailUrl;
		}

		return this.getFileIcon(file.mimetype);
	}

	togglePresentation() {
		this.props.onSetPresentation(this.props.index);
	}

	get isPresentation() {
		return this.props.index === this.props.presentationId;
	}

	prev() {
		const len = this.props.files.length;
		const currentPos = this.props.files.findIndex(
			(f) => f.id === this.props.index
		);
		if (currentPos === -1) return;
		const prevPos = (currentPos + len - 1) % len;
		const prevId = this.props.files[prevPos].id;
		this.props.onNavigate?.(prevId);
		this.state.loading = true;
	}

	next() {
		const len = this.props.files.length;
		const currentPos = this.props.files.findIndex(
			(f) => f.id === this.props.index
		);
		if (currentPos === -1) return;
		const nextPos = (currentPos + 1) % len;
		const nextId = this.props.files[nextPos].id;
		this.props.onNavigate?.(nextId);
		this.state.loading = true;
	}

	close() {
		this.props.onClose();
	}

	async deleteCurrent() {
		this.state.loading = true;
		if (this.props.files.length > 1) this.next();
		try {
			await this.props.onDelete(this.props.index);
		} finally {
			this.state.loading = false;
		}
	}
}
