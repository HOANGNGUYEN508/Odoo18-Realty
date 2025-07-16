import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useX2ManyCrud } from "@web/views/fields/relational_utils";
import { Component, useState, onWillStart } from "@odoo/owl";
import { PhotoLightbox } from "./photo_lightbox";
import { ValidatedFileInput } from './validated_file_input';
import { rpc } from "@web/core/network/rpc";

const MIME_EXT_MAP = {
  "image/jpeg": ".jpg",
  "image/png":  ".png",
  "image/gif":  ".gif",
  "image/webp": ".webp",
  "image/bmp":  ".bmp",
};

export class Many2ManyImageField extends Component {
  static template = "realty_bds.Many2ManyImageField";
  static components = { ValidatedFileInput, PhotoLightbox };
  static props = {
    id:                     { type: String,  optional: true },
    name:                   { type: String },
    readonly:               { type: Boolean, optional: true },
    record:                 { type: Object },
    acceptedFileExtensions: { type: String,  optional: true },
    className:              { type: String,  optional: true },
    numberOfFiles:          { type: Number,  optional: true },
    fileSize:               { type: Number,  optional: true},
    rowHeight:              { type: Number,  optional: true },
    gutter:                 { type: Number,  optional: true },
  };
  static defaultProps = {
    numberOfFiles: 5,
    fileSize:      5 * 1024 * 1024,
    rowHeight:     140,
    gutter:        8,
  };

  setup() {
    this.orm = useService("orm");
    this.notification = useService("notification");
    this.operations = useX2ManyCrud(
      () => this.props.record.data[this.props.name],
      true
    );
    this.state = useState({ 
      lightboxIndex:  -1,
      presentationId: -1,
      maxFiles:       this.props.numberOfFiles - this.files.length,
      isDragOver:     false,
    });

		this.fileInputAPI = useState({
      processFiles: null,
    });

    this.openLightbox =     this.openLightbox.bind(this);
    this.closeLightbox =    this.closeLightbox.bind(this);
    this.navigateLightbox = this.navigateLightbox.bind(this);
    this.onFileRemove =     this.onFileRemove.bind(this);
    this.setPresentation =  this.setPresentation.bind(this);
    this.onDragOver =       this.onDragOver.bind(this);
    this.onDragLeave =      this.onDragLeave.bind(this);
    this.onDrop =           this.onDrop.bind(this);

    onWillStart(async () => {
      const { resId, resModel } = this.props.record;
      if (resId) {
        try {
          const [data] = await this.orm.read(resModel, [resId], [
            "presentation_image_id",
          ]);
          this.state.presentationId = data.presentation_image_id || -1;
        } catch (err) {
          console.error("Failed to fetch presentation_image_id:", err);
        }
      }
    });
  }

  get files() {
    return this.props.record.data[this.props.name].records.map((record) => {
      return {
        id: record.resId,
        name: record.data.name,
        url: this.getUrl(record.resId)
      };
    });
  }

  get msm() {
    return `Upload up to ${this.props.numberOfFiles} images.`;
  }

  getUrl(id) {
    return `/web/content/${id}?download=true`;
  }

  async setPresentation(attachmentId) {
    const { resId, resModel } = this.props.record;
    if (resId) {
      await this.orm.call(resModel, 'set_presentation_image', [[resId], attachmentId]);
      this.state.presentationId = attachmentId;
    }
  }

  async prepareData(data, salt) {
    try {
      const result = await rpc('/compute_hash_img_string', {
        salt: salt,
        data: data,
      });
      return { result: `${result.hash}` };
    } catch (error) {
      console.error("Hash computation failed:", error);
      return { result: data };
    }
  }

  async onFileUploaded(files) {
    for (const file of files) {
      const result = await this.prepareData(file.filename, file.id);
      await this.operations.saveRecord([file.id]);
      await this.orm.call("ir.attachment", "write", [[file.id], { name: `${result.result}${MIME_EXT_MAP[file.mimetype] || ""}` }]);
    }
    // Update maxFiles after upload
    this.state.maxFiles = this.props.numberOfFiles - this.files.length;
  }

  handleValidationErrors(errors) {
    errors.forEach(({ file, error }) => {
      const fileName = file.name || _t("Unknown file");
      this.notification.add(
        `${fileName}: ${error.message}`, 
        {
          title: _t("Uploading error"),
          type: "danger",
        }
      );
    });
  }

  async onFileRemove(deleteId, fromGrid = false) {
    const files = this.files;
    const currentIdx = files.findIndex(f => f.id === deleteId);
    if (currentIdx === -1) return;

    const recs = this.props.record.data[this.props.name].records;
    const toDelete = recs.find(r => r.resId === deleteId);
    await this.operations.removeRecord(toDelete);

    const remaining = this.files;
    this.state.maxFiles = this.props.numberOfFiles - remaining.length;
		// if delete from PhotoLightbox
		if (!fromGrid) {
			if (remaining.length === 0) {
				this.closeLightbox();
				return;
			}

			const nextPos = currentIdx >= remaining.length
				? 0
				: currentIdx;

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
    { label: _t("Accepted file extensions"), name: "accepted_file_extensions", type: "string" },
    { label: _t("Number of files"),          name: "number_of_files",          type: "integer" },
    { label: _t("Row height"),               name: "row_height",               type: "integer" },
    { label: _t("Gutter size"),              name: "gutter",                   type: "integer" },
  ],
  supportedTypes: ["many2many"],
  isEmpty: () => false,
  relatedFields: [
    { name: "name",     type: "char" },
    { name: "mimetype", type: "char" },
  ],
  extractProps: ({ attrs, options }) => ({
    acceptedFileExtensions: options.accepted_file_extensions,
    className: attrs.class,
    numberOfFiles: options.number_of_files,
    fileSize: options.file_size,
    rowHeight: options.row_height,
    gutter: options.gutter,
  }),
};

registry.category("fields").add("many2many_image", many2ManyImageField);