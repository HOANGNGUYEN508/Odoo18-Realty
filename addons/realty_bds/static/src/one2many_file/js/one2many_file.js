import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";
import { PhotoLightbox } from "../../many2many_image/js/photo_lightbox";
import { IMAGE_MIMETYPES, FILE_TYPE_ICONS } from "../../many2many_image/js/constants";

export class One2ManyFile extends Component {
	static template = "realty_bds.One2ManyFile";
	static components = { PhotoLightbox };
	static props = {
		id: { type: String, optional: true },
		name: { type: String },
		readonly: { type: Boolean, optional: true },
		record: { type: Object },
		className: { type: String, optional: true },
		rowHeight: { type: Number, optional: true },
		gutter: { type: Number, optional: true },
	};
	static defaultProps = {
		rowHeight: 140,
		gutter: 8,
		readonly: true,
	};

	setup() {
		this.orm = useService("orm");
		this.state = useState({
			lightboxIndex: -1,
		});

		this._attachmentMeta = {}; // id -> { id, name, mimetype }

		this.resId = this.props.record.resId;
		this.resModel = this.props.record.resModel;

		this.openLightbox = this.openLightbox.bind(this);
		this.closeLightbox = this.closeLightbox.bind(this);
		this.navigateLightbox = this.navigateLightbox.bind(this);

		onWillStart(async () => {
			const records = this.props.record.data[this.props.name].records;
			if (records && records.length > 0) {
				const ids = records.map((r) => r.resId);
				await this.loadAttachmentMetas(ids);
			}
		});
	}

	get files() {
		return this.props.record.data[this.props.name].records.map((record) => {
			const id = record.resId;
			const meta = this._attachmentMeta[id] || record.data || {};
			const mimetype = meta.mimetype || record.data?.mimetype || "";
			const isImage = IMAGE_MIMETYPES.includes(mimetype);
			
			return {
				id,
				name: meta.name || record.data?.name || "",
				mimetype,
				isImage,
				url: this.getUrl(id),
				thumbnailUrl: isImage ? this.getUrl(id) : this.getFileIcon(mimetype),
			};
		});
	}

	getUrl(id) {
		return `/web/content/${id}?download=true`;
	}

	getFileIcon(mimetype) {
		return FILE_TYPE_ICONS[mimetype] || "/web/static/src/img/mimetypes/binary.svg";
	}

	async loadAttachmentMetas(ids = []) {
		const toLoad = ids.filter((id) => !this._attachmentMeta[id]);
		if (!toLoad.length) return;
		
		try {
			const attachments = await this.orm.read(
				"ir.attachment",
				toLoad,
				["id", "name", "mimetype"]
			);
			
			attachments.forEach((att) => {
				this._attachmentMeta[att.id] = {
					id: att.id,
					name: att.name,
					mimetype: att.mimetype,
				};
			});
			
			// Mark missing ids as empty to avoid repeated retries
			toLoad.forEach((id) => {
				if (!this._attachmentMeta[id]) {
					this._attachmentMeta[id] = {};
				}
			});
		} catch (e) {
			console.warn("loadAttachmentMetas failed", e);
			toLoad.forEach((id) => (this._attachmentMeta[id] = {}));
		}
	}

	navigateLightbox(newIndex) {
		this.state.lightboxIndex = newIndex;
	}

	openLightbox(idx) {
		this.state.lightboxIndex = idx;
	}

	closeLightbox() {
		this.state.lightboxIndex = -1;
	}
}

export const One2ManyFileField = {
	component: One2ManyFile,
	supportedOptions: [
		{ label: _t("Row height"), name: "row_height", type: "integer" },
		{ label: _t("Gutter size"), name: "gutter", type: "integer" },
	],
	supportedTypes: ["one2many"],
	isEmpty: () => false,
	extractProps: ({ attrs, options }) => ({
		readonly: attrs.readonly === "1",
		className: attrs.class,
		rowHeight: options.row_height,
		gutter: options.gutter,
	}),
};

registry.category("fields").add("one2many_file", One2ManyFileField);