import { Component, onMounted, useRef, useState } from "@odoo/owl";
import { useFileUploader } from "@web/core/utils/files";

export class ValidatedFileInput extends Component {
	static template = "web.FileInput";
	static defaultProps = {
		acceptedFileExtensions: "*",
		hidden: false,
		multiUpload: false,
		onUpload: () => {},
		onValidationError: () => {},
		route: "/web/binary/upload_attachment",
		beforeOpen: async () => true,
		maxFiles: null,
		maxFileSize: null,
	};
	static props = {
		onMounted: { type: Function, optional: true },
		acceptedFileExtensions: { type: String, optional: true },
		autoOpen: { type: Boolean, optional: true },
		hidden: { type: Boolean, optional: true },
		multiUpload: { type: Boolean, optional: true },
		onUpload: { type: Function, optional: true },
		onValidationError: { type: Function, optional: true },
		beforeOpen: { type: Function, optional: true },
		resId: { type: Number, optional: true },
		resModel: { type: String, optional: true },
		route: { type: String, optional: true },
		maxFiles: { type: Number, optional: true },
		maxFileSize: { type: Number, optional: true },
		"*": true,
	};

	setup() {
		this.uploadFiles = useFileUploader();
		this.fileInputRef = useRef("file-input");
		this.state = useState({
			isDisable: false,
		});

		onMounted(() => {
			if (this.props.autoOpen) {
				this.onTriggerClicked();
			}
			if (this.props.onMounted) {
				this.props.onMounted({
					processFiles: this.processFiles.bind(this),
				});
			}
		});
	}

	getHttpParams(files) {
		const { resId, resModel } = this.props;
		const params = {
			csrf_token: odoo.csrf_token,
			ufile: files,
		};
		if (resModel) {
			params.model = resModel;
		}
		if (resId !== undefined) {
			params.id = resId;
		}
		return params;
	}

	// Format bytes to human-readable format
	formatFileSize(bytes) {
		if (bytes === 0) return "0 Bytes";
		const k = 1024;
		const sizes = ["Bytes", "KB", "MB", "GB"];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
	}

	// Create a FileList-like object from an array of files
	createFileListLike(files) {
		const fileList = {
			length: files.length,
			item: (index) => files[index],
			[Symbol.iterator]: function* () {
				for (let i = 0; i < this.length; i++) {
					yield this.item(i);
				}
			},
		};
		return fileList;
	}

	// Public method to process files (for drag and drop)
	async processFiles(files) {
		// Create a synthetic event
		const event = {
			target: {
				files: this.createFileListLike(files),
			},
		};
		await this.onFileInputChange(event);
	}

	//--------------------------------------------------------------------------
	// Handlers
	//--------------------------------------------------------------------------

	async onFileInputChange(ev) {
		this.state.isDisable = true;
		const fileList = ev.target.files;
		const allFiles = Array.from(fileList);
		const errors = [];
		const validFiles = [];

		// Process files in order
		for (const file of allFiles) {
			// Check if we've reached max files limit
			if (this.props.maxFiles && validFiles.length >= this.props.maxFiles) {
				errors.push({
					file,
					error: new Error(
						`Skipped - Only ${this.props.maxFiles} file(s) allowed`
					),
				});
				continue;
			}

			// Check file size
			if (this.props.maxFileSize && file.size > this.props.maxFileSize) {
				errors.push({
					file,
					error: new Error(
						`File too large (${this.formatFileSize(
							file.size
						)} > ${this.formatFileSize(this.props.maxFileSize)})`
					),
				});
				continue;
			}

			// All checks passed
			validFiles.push(file);
		}

		// Report validation errors
		if (errors.length > 0) {
			this.props.onValidationError(errors);
		}

		try {
			// Upload valid files if any
			if (validFiles.length > 0) {
				const httpParams = this.getHttpParams(validFiles);
				const parsedFileData = await this.uploadFiles(
					this.props.route,
					httpParams
				);

				if (parsedFileData) {
					this.props.onUpload(parsedFileData, validFiles);
				}
			}
		} catch (uploadError) {
			console.error("Upload error:", uploadError);
			// Convert upload error to validation-like error
			const uploadErrors = validFiles.map((file) => ({
				file,
				error: new Error(`Upload failed: ${uploadError.message}`),
			}));
			this.props.onValidationError(uploadErrors);
		} finally {
			this.fileInputRef.el.value = null;
			this.state.isDisable = false;
		}
	}

	async onTriggerClicked() {
		if (await this.props.beforeOpen()) {
			this.fileInputRef.el.click();
		}
	}
}
