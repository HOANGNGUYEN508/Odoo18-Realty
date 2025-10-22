import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { Component, useState, onWillStart } from "@odoo/owl";
import { PhotoLightbox } from "./photo_lightbox";
import { ValidatedFileInput } from "./validated_file_input";
import { rpc } from "@web/core/network/rpc";

const MIME_EXT_MAP = {
	"image/jpeg": ".jpg",
	"image/png": ".png",
	"image/gif": ".gif",
	"image/webp": ".webp",
	"image/bmp": ".bmp",
};

export class Many2ManyImageField extends Component {
	static template = "realty_bds.Many2ManyImageField";
	static components = { ValidatedFileInput, PhotoLightbox };
	static props = {
		id: { type: String, optional: true },
		name: { type: String },
		readonly: { type: Boolean, optional: true },
		record: { type: Object },
		presentationImage: { type: Boolean, optional: true },
		isPublic: { type: Boolean, optional: true },
		acceptedFileExtensions: { type: String, optional: true },
		className: { type: String, optional: true },
		numberOfFiles: { type: Number, optional: true },
		fileSize: { type: Number, optional: true },
		rowHeight: { type: Number, optional: true },
		gutter: { type: Number, optional: true },
	};
	static defaultProps = {
		numberOfFiles: 5,
		fileSize: 5 * 1024 * 1024,
		rowHeight: 140,
		gutter: 8,
		presentationImage: false,
		readonly: false,
		isPublic: false,
	};

	setup() {
		this.orm = useService("orm");
		this.notification = useService("notification");
		this.operations = useX2ManyCrud(
			() => this.props.record.data[this.props.name],
			true
		);
		this.state = useState({
			lightboxIndex: -1,
			presentationId: -1,
			maxFiles: 0, // will be initialized after onWillStart to avoid call something that have not been loaded yet
			isDragOver: false,
		});

		this.fileInputAPI = useState({
			processFiles: null,
		});

		this._attachmentMeta = {}; // id -> { id, name, mimetype }

		this.resId = this.props.record.resId;
		this.resModel = this.props.record.resModel;
		this.isPublic = this.props.isPublic;

		this.openLightbox = this.openLightbox.bind(this);
		this.closeLightbox = this.closeLightbox.bind(this);
		this.navigateLightbox = this.navigateLightbox.bind(this);
		this.onFileRemove = this.onFileRemove.bind(this);
		this.setPresentation = this.setPresentation.bind(this);
		this.onDragOver = this.onDragOver.bind(this);
		this.onDragLeave = this.onDragLeave.bind(this);
		this.onDrop = this.onDrop.bind(this);

		// onWillStart: fetch presentation id if needed + initialize metadata
		onWillStart(async () => {
			if (this.props.presentationImage) {
				if (this.resId) {
					try {
						const [data] = await this.orm.read(
							this.resModel,
							[this.resId],
							["presentation_image_id"]
						);
						this.state.presentationId = data.presentation_image_id || -1;
					} catch (err) {
						console.error("Failed to fetch presentation_image_id:", err);
					}
				}
			}
			const records = this.props.record.data[this.props.name].records;
			if (records && records.length > 0) {
				const ids = records
					.map((r) => r.resId)
					.slice(0, this.props.numberOfFiles);
				await this.loadAttachmentMetasFastPath(ids);
			}
		});
		this.state.maxFiles = this.props.numberOfFiles - this.files.length;
	}

	get files() {
		// fallback safe: prefer cached meta, else record.data, else empty name
		return this.props.record.data[this.props.name].records.map((record) => {
			const id = record.resId;
			const meta = this._attachmentMeta[id] || record.data || {};
			return {
				id,
				name: meta.name || record.data?.name || "",
				url: this.getUrl(id),
			};
		});
	}

	get msm() {
		return `Upload up to ${this.props.numberOfFiles} images.`;
	}

	getUrl(id) {
		return `/web/content_protected/${id}?download=true&model=${this.resModel}&field=${this.props.name}`;
	}

	/**
	 * Ask the server to run the *fast-path-only* permission checks for the given ids,
	 * and return metadata only for those attachment ids where fast-path passed.
	 * The server returns a map { "<id>": {id, name, mimetype}, ... }.
	 */
	async loadAttachmentMetasFastPath(ids = []) {
		const toLoad = ids.filter((id) => !this._attachmentMeta[id]);
		if (!toLoad.length) return;
		try {
			const resp = await rpc("/realty/attachment/meta_fastpath", {
				attachment_ids: toLoad,
				model: this.resModel,
				field: this.props.name,
			});
			Object.entries(resp || {}).forEach(([k, v]) => {
				const id = parseInt(k, 10);
				this._attachmentMeta[id] = v || {};
			});
			// mark missing ids as empty to avoid repeated retries
			toLoad.forEach((id) => {
				if (!this._attachmentMeta[id]) this._attachmentMeta[id] = {};
			});
		} catch (e) {
			console.warn("loadAttachmentMetasFastPath failed", e);
			toLoad.forEach((id) => (this._attachmentMeta[id] = {}));
		}
	}

	async setPresentation(attachmentId) {
		if (this.resId) {
			await this.orm.call(this.resModel, "set_presentation_image", [
				[this.resId],
				attachmentId,
			]);
			this.state.presentationId = attachmentId;
		}
	}

	async prepareData(data, salt) {
		try {
			const result = await rpc("/compute_hash_img_string", {
				salt: salt,
				data: data,
			});
			return { result: `${result.hash}` };
		} catch (error) {
			console.warn("Hash computation failed:", error);
			return { result: data };
		}
	}

	async onFileUploaded(files) {
		for (const file of files) {
			const result = await this.prepareData(file.filename, file.id);
			await this.operations.saveRecord([file.id]);
			await this.orm.call("ir.attachment", "write", [
				[file.id],
				{
					name: `${result.result}${MIME_EXT_MAP[file.mimetype] || ""}`,
					public: this.isPublic,
				},
			]);
		}

		// Update data after upload
		const newIds = files.map((f) => f.id);
		await this.loadAttachmentMetasFastPath(newIds);
		this.state.maxFiles = this.props.numberOfFiles - this.files.length;
	}

	handleValidationErrors(errors) {
		errors.forEach(({ file, error }) => {
			const fileName = file.name || _t("Unknown file");
			this.notification.add(`${fileName}: ${error.message}`, {
				title: _t("Uploading error"),
				type: "danger",
			});
		});
	}

	async onFileRemove(deleteId, fromGrid = false) {
		const files = this.files;
		const currentIdx = files.findIndex((f) => f.id === deleteId);
		if (currentIdx === -1) return;

		const recs = this.props.record.data[this.props.name].records;
		const toDelete = recs.find((r) => r.resId === deleteId);
		await this.operations.removeRecord(toDelete);

		try {
				// call ir..attachment method: mark_orphaned
				await this.orm.call("ir.attachment", "mark_orphaned", [[deleteId], this.resModel, this.resId]);
		} catch (err) {
				console.warn("mark_orphaned failed for attachment", deleteId, err);
		}

		// remove cached meta
		if (this._attachmentMeta[deleteId]) delete this._attachmentMeta[deleteId];

		const remaining = this.files;
		this.state.maxFiles = this.props.numberOfFiles - remaining.length;
		// if delete from PhotoLightbox
		if (!fromGrid) {
			if (remaining.length === 0) {
				this.closeLightbox();
				return;
			}

			const nextPos = currentIdx >= remaining.length ? 0 : currentIdx;

			const nextId = remaining[nextPos].id;
			this.state.lightboxIndex = nextId;
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

	onDragOver(ev) {
		ev.preventDefault();
		ev.stopPropagation();
		if (this.state.lightboxIndex === -1 && this.state.maxFiles > 0) {
			this.state.isDragOver = true;
		}
	}

	onDragLeave(ev) {
		ev.preventDefault();
		ev.stopPropagation();
		this.state.isDragOver = false;
	}

	async onDrop(ev) {
		ev.preventDefault();
		ev.stopPropagation();
		this.state.isDragOver = false;

		if (this.state.lightboxIndex !== -1 || this.state.maxFiles <= 0) return;

		const files = Array.from(ev.dataTransfer.files);
		if (files.length === 0) return;

		if (this.fileInputAPI.processFiles) {
			await this.fileInputAPI.processFiles(files);
		}
	}
}

export const many2ManyImageField = {
	component: Many2ManyImageField,
	supportedOptions: [
		{
			label: _t("Accepted file extensions"),
			name: "accepted_file_extensions",
			type: "string",
		},
		{ label: _t("Number of files"), name: "number_of_files", type: "integer" },
		{ label: _t("Row height"), name: "row_height", type: "integer" },
		{ label: _t("Gutter size"), name: "gutter", type: "integer" },
		{ label: _t("File size"), name: "file_size", type: "integer" },
		{
			label: _t("Use Presentation Image Feature?"),
			name: "presentation_image",
			type: "boolean",
		},
		{
			label: _t("Make uploaded images public?"),
			name: "public_file",
			type: "boolean",
		},
	],
	supportedTypes: ["many2many"],
	isEmpty: () => false,
	// relatedFields removed intentionally to avoid protected prefetch issues
	extractProps: ({ attrs, options }) => ({
		acceptedFileExtensions: options.accepted_file_extensions,
		presentationImage: options.presentation_image,
		readonly: attrs.readonly === "1",
		className: attrs.class,
		numberOfFiles: options.number_of_files,
		fileSize: options.file_size,
		rowHeight: options.row_height,
		gutter: options.gutter,
		isPublic: options.is_public || false,
	}),
};

registry.category("fields").add("many2many_image", many2ManyImageField);
