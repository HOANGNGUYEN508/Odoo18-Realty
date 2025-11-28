import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.FileUploadComponent = publicWidget.Widget.extend({
	selector: "#file_upload_component",
	events: {
		'change input[type="file"]': "_onFileChange",
		"click .file-upload-area": "_triggerFileInput",
		"click .remove-file-btn": "_removeFile",
		"click .preview-file": "_openLightbox",
		"dragover .file-upload-area": "_onDragOver",
		"dragleave .file-upload-area": "_onDragLeave",
		"drop .file-upload-area": "_onDrop",
	},

	start: function () {
		this.$fileInput = this.$el.find('input[type="file"]');
		this.$uploadArea = this.$el.find(".file-upload-area");
		this.$fileList = this.$el.find("#file_list");
		this.$fileErrors = this.$el.find("#file_errors");
		this.$lightbox = null;
		this.currentLightboxIndex = -1;

		// Allowed file types
		this.allowedTypes = {
			"image/jpeg": { ext: ".jpg", icon: "fa-file-image-o", preview: true },
			"image/png": { ext: ".png", icon: "fa-file-image-o", preview: true },
			"image/gif": { ext: ".gif", icon: "fa-file-image-o", preview: true },
			"image/webp": { ext: ".webp", icon: "fa-file-image-o", preview: true },
			"application/pdf": { ext: ".pdf", icon: "fa-file-pdf-o", preview: false },
			"application/msword": {
				ext: ".doc",
				icon: "fa-file-word-o",
				preview: false,
			},
			"application/vnd.openxmlformats-officedocument.wordprocessingml.document":
				{ ext: ".docx", icon: "fa-file-word-o", preview: false },
		};

		this.maxSize = 10 * 1024 * 1024; // 10MB
		this.maxFiles = 5;
		this.uploadedFiles = [];
		this._attachFormSubmitHandler();
		return this._super.apply(this, arguments);
	},

	_attachFormSubmitHandler: function () {
		const self = this;
		const $form = this.$el.closest("form");

		if ($form.length) {
			$form.on("submit.fileupload", function (e) {
				self._syncFilesToInput();
			});
		}
	},

	_syncFilesToInput: function () {
		if (this.uploadedFiles.length === 0) {
			// Clear the input if no files
			this.$fileInput.val("");
			return;
		}

		try {
			// Create a DataTransfer object to hold the files
			const dt = new DataTransfer();

			// Add all uploaded files to the DataTransfer
			this.uploadedFiles.forEach((fileData) => {
				dt.items.add(fileData.file);
			});

			// Assign the files to the input element
			this.$fileInput[0].files = dt.files;

			console.log("Synced", dt.files.length, "files to input element");
		} catch (error) {
			console.error("Error syncing files to input:", error);
			// Fallback: If DataTransfer fails, warn the user
			alert("Error preparing files for upload. Please try again.");
		}
	},

	_triggerFileInput: function (e) {
		if (e && e.target.closest(".remove-file-btn, .preview-file")) {
			return;
		}
		e.preventDefault();
		if (this.uploadedFiles.length < this.maxFiles) {
			this.$fileInput.click();
		}
	},

	_onFileChange: function (e) {
		const files = Array.from(e.target.files);
		this._processFiles(files);
	},

	_onDragOver: function (e) {
		e.preventDefault();
		e.stopPropagation();
		if (this.uploadedFiles.length < this.maxFiles) {
			this.$uploadArea.addClass("drag-over");
		}
	},

	_onDragLeave: function (e) {
		e.preventDefault();
		e.stopPropagation();
		this.$uploadArea.removeClass("drag-over");
	},

	_onDrop: function (e) {
		e.preventDefault();
		e.stopPropagation();
		this.$uploadArea.removeClass("drag-over");

		if (this.uploadedFiles.length >= this.maxFiles) {
			return;
		}

		const files = Array.from(e.originalEvent.dataTransfer.files);
		if (files.length > 0) {
			this._processFiles(files);
		}
	},

	_processFiles: function (files) {
		this.$fileErrors.addClass("d-none").html("");
		const errors = [];

		for (const file of files) {
			// Check file limit
			if (this.uploadedFiles.length >= this.maxFiles) {
				errors.push(`Only ${this.maxFiles} files allowed`);
				break;
			}

			// Validate file type
			if (!this.allowedTypes[file.type]) {
				errors.push(`${file.name}: Invalid file type`);
				continue;
			}

			// Validate file size
			if (file.size > this.maxSize) {
				errors.push(`${file.name}: File size exceeds 10MB`);
				continue;
			}

			// Check for duplicates
			const isDuplicate = this.uploadedFiles.some(
				(f) => f.name === file.name && f.size === file.size
			);
			if (isDuplicate) {
				errors.push(`${file.name}: File already added`);
				continue;
			}

			// Add file
			const fileInfo = this.allowedTypes[file.type];
			const fileData = {
				file: file,
				name: file.name,
				size: file.size,
				type: file.type,
				icon: fileInfo.icon,
				canPreview: fileInfo.preview,
				url: null,
			};

			// Create preview URL for images
			if (fileInfo.preview) {
				fileData.url = URL.createObjectURL(file);
			}

			this.uploadedFiles.push(fileData);
		}

		if (errors.length > 0) {
			this.$fileErrors.removeClass("d-none").html(errors.join("<br>"));
		}

		this._renderFileList();
		this._updateUploadArea();
	},

	_renderFileList: function () {
		this.$fileList.empty();

		this.uploadedFiles.forEach((fileData, index) => {
			const $item = $(`
				<div class="file-item" data-index="${index}">
					<div class="file-preview">
						${
							fileData.canPreview
								? `<img src="${fileData.url}" alt="${fileData.name}" />`
								: `<i class="fa ${fileData.icon} fa-3x text-muted"></i>`
						}
					</div>
					<div class="file-info">
						<div class="file-name" title="${fileData.name}">${fileData.name}</div>
						<div class="file-size">${this._formatFileSize(fileData.size)}</div>
					</div>
					<div class="file-actions">
						<button type="button" class="btn btn-sm btn-primary preview-file" data-index="${index}">
							<i class="fa fa-eye"></i>
						</button>
						<button type="button" class="btn btn-sm btn-danger remove-file-btn" data-index="${index}">
							<i class="fa fa-trash"></i>
						</button>
					</div>
				</div>
			`);
			this.$fileList.append($item);
		});
	},

	_updateUploadArea: function () {
		if (this.uploadedFiles.length >= this.maxFiles) {
			this.$uploadArea.addClass("disabled");
		} else {
			this.$uploadArea.removeClass("disabled");
		}
	},

	_removeFile: function (e) {
		e.preventDefault();
		e.stopPropagation();

		const index = parseInt($(e.currentTarget).data("index"));
		const fileData = this.uploadedFiles[index];

		// Revoke object URL if exists
		if (fileData.url) {
			URL.revokeObjectURL(fileData.url);
		}

		this.uploadedFiles.splice(index, 1);
		this._renderFileList();
		this._updateUploadArea();
		this.$fileErrors.addClass("d-none").html("");
	},

	_openLightbox: function (e) {
		e.preventDefault();
		e.stopPropagation();

		const index = parseInt($(e.currentTarget).data("index"));
		this.currentLightboxIndex = index;
		// Create the lightbox if not created already, then update content & show
		this._createLightboxIfNeeded();
		this._updateLightboxContent();
		this.$lightbox.css("display", "flex");
	},

	_createLightboxIfNeeded: function () {
		// If already created, nothing to do
		if (this.$lightbox) {
			return;
		}

		// Build DOM once
		this.$lightbox = $(`
				<div class="lightbox-backdrop">
						<div class="lightbox-content">
								<div class="lightbox-header d-flex justify-content-between align-items-center">
										<span class="lightbox-filename"></span>
										<div class="lightbox-controls">
												<button type="button" class="btn btn-link lightbox-delete" title="Delete">
														<i class="fa fa-trash fa-lg text-white"></i>
												</button>
												<button type="button" class="btn btn-link lightbox-close" title="Close">
														<i class="fa fa-times fa-2x text-white"></i>
												</button>
										</div>
								</div>
								<div class="lightbox-body d-flex align-items-center justify-content-center">
										<button type="button" class="btn btn-link lightbox-nav lightbox-prev" title="Previous">
												<i class="fa fa-chevron-left fa-3x"></i>
										</button>

										<div class="lightbox-inner-content text-center" style="max-width:80%; min-height:200px;">
												<!-- dynamic content (img or file preview) goes here -->
										</div>

										<button type="button" class="btn btn-link lightbox-nav lightbox-next" title="Next">
												<i class="fa fa-chevron-right fa-3x"></i>
										</button>
								</div>
								<div class="lightbox-footer text-center mt-3">
										<span class="lightbox-counter"></span>
								</div>
						</div>
				</div>
		`);

		// Append once
		$("body").append(this.$lightbox);

		// Cache commonly-updated elements for faster updates
		this.$lightboxInner = this.$lightbox.find(".lightbox-inner-content");
		this.$lightboxFilename = this.$lightbox.find(".lightbox-filename");
		this.$lightboxCounter = this.$lightbox.find(".lightbox-counter");
		this.$lightboxPrev = this.$lightbox.find(".lightbox-prev");
		this.$lightboxNext = this.$lightbox.find(".lightbox-next");
		this.$lightboxDelete = this.$lightbox.find(".lightbox-delete");
		this.$lightboxClose = this.$lightbox.find(".lightbox-close");
		this.$lightboxBackdrop = this.$lightbox; // the top-level backdrop

		const self = this;

		// Bind handlers ONCE (namespaced)
		this.$lightbox.on("click.lightbox", ".lightbox-close", function (ev) {
			ev.preventDefault();
			ev.stopPropagation();
			self._closeLightboxButton(ev);
		});

		this.$lightbox.on("click.lightbox", ".lightbox-delete", function (ev) {
			ev.preventDefault();
			ev.stopPropagation();
			self._deleteFromLightbox(ev);
		});

		this.$lightbox.on("click.lightbox", ".lightbox-prev", function (ev) {
			ev.preventDefault();
			ev.stopPropagation();
			self._navigatePrev(ev);
		});

		this.$lightbox.on("click.lightbox", ".lightbox-next", function (ev) {
			ev.preventDefault();
			ev.stopPropagation();
			self._navigateNext(ev);
		});

		// Clicking on backdrop (outside content) should close
		this.$lightbox.on("click.lightbox", ".lightbox-backdrop", function (ev) {
			// ensure only clicks directly on backdrop close it (not on children)
			if (ev.target === this) {
				self._destroyLightbox();
			}
		});

		// Prevent clicks inside content from bubbling to backdrop
		this.$lightbox.on("click.lightbox", ".lightbox-content", function (ev) {
			ev.stopPropagation();
		});

		// Initially hide; _openLightbox will show
		this.$lightbox.hide();
	},

	_updateLightboxContent: function () {
		// Safety
		if (
			!this.$lightbox ||
			this.currentLightboxIndex < 0 ||
			this.currentLightboxIndex >= this.uploadedFiles.length
		) {
			// If out of range, close
			this._destroyLightbox();
			return;
		}

		const fileData = this.uploadedFiles[this.currentLightboxIndex];

		// Update filename and counter
		this.$lightboxFilename.text(fileData.name || "");
		this.$lightboxCounter.text(
			this.currentLightboxIndex + 1 + " / " + this.uploadedFiles.length
		);

		// Update prev/next visibility (optional; you can keep looping behavior if you want)
		if (this.uploadedFiles.length <= 1) {
			this.$lightboxPrev.hide();
			this.$lightboxNext.hide();
		} else {
			this.$lightboxPrev.show();
			this.$lightboxNext.show();
		}

		// Replace the inner content efficiently without touching event bindings
		// Clear previous content but keep the inner container node
		this.$lightboxInner.empty();

		if (fileData.canPreview) {
			// For images, use <img> with objectURL
			const $img = $(
				`<img class="lightbox-image img-fluid" alt="${fileData.name}" />`
			);
			// set src (fileData.url is the objectURL created earlier)
			$img.attr("src", fileData.url);
			this.$lightboxInner.append($img);
		} else {
			// For non-preview files, show icon + details
			const $non = $(`
            <div class="lightbox-file-preview">
                <i class="fa ${fileData.icon} fa-5x text-muted mb-3"></i>
                <h4 class="mb-1">${fileData.name}</h4>
                <p class="text-muted">${this._formatFileSize(fileData.size)}</p>
            </div>
        `);
			this.$lightboxInner.append($non);
		}

		// Ensure it's visible
		this.$lightbox.show();
	},

	_destroyLightbox: function () {
		if (this.$lightbox) {
			// Unbind namespaced handlers and remove DOM
			this.$lightbox.off(".lightbox");
			this.$lightbox.remove();
			this.$lightbox = null;
			this.$lightboxInner = null;
			this.$lightboxFilename = null;
			this.$lightboxCounter = null;
			this.$lightboxPrev = null;
			this.$lightboxNext = null;
			this.$lightboxDelete = null;
			this.$lightboxClose = null;
			this.currentLightboxIndex = -1;
		}
	},

	_closeLightboxButton: function (e) {
		e.preventDefault();
		e.stopPropagation();
		this._destroyLightbox();
	},

	_deleteFromLightbox: function (e) {
		e.preventDefault();
		e.stopPropagation();

		if (
			this.currentLightboxIndex < 0 ||
			this.currentLightboxIndex >= this.uploadedFiles.length
		) {
			return;
		}

		const fileData = this.uploadedFiles[this.currentLightboxIndex];

		// revoke objectURL if present
		if (fileData && fileData.url) {
			try {
				URL.revokeObjectURL(fileData.url);
			} catch (err) {
				/* ignore */
			}
		}

		// remove the file
		this.uploadedFiles.splice(this.currentLightboxIndex, 1);

		// If no files left -> destroy
		if (this.uploadedFiles.length === 0) {
			this._renderFileList(); // update UI
			this._destroyLightbox();
			return;
		}

		// Adjust current index if needed
		if (this.currentLightboxIndex >= this.uploadedFiles.length) {
			this.currentLightboxIndex = this.uploadedFiles.length - 1;
		}

		// Refresh file list UI and lightbox content only
		this._renderFileList();
		this._updateLightboxContent();
	},

	_navigatePrev: function (e) {
		e.preventDefault();
		e.stopPropagation();

		if (this.uploadedFiles.length <= 1) {
			return;
		}
		this.currentLightboxIndex--;
		if (this.currentLightboxIndex < 0) {
			this.currentLightboxIndex = this.uploadedFiles.length - 1;
		}
		// just update content — no rebind
		this._updateLightboxContent();
	},

	_navigateNext: function (e) {
		e.preventDefault();
		e.stopPropagation();

		if (this.uploadedFiles.length <= 1) {
			return;
		}
		this.currentLightboxIndex++;
		if (this.currentLightboxIndex >= this.uploadedFiles.length) {
			this.currentLightboxIndex = 0;
		}
		// just update content — no rebind
		this._updateLightboxContent();
	},

	_stopPropagation: function (e) {
		e.stopPropagation();
	},

	_formatFileSize: function (bytes) {
		if (bytes === 0) return "0 Bytes";
		const k = 1024;
		const sizes = ["Bytes", "KB", "MB", "GB"];
		const i = Math.floor(Math.log(bytes) / Math.log(k));
		return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
	},

	// Public method to get files for form submission
	getFiles: function () {
		return this.uploadedFiles.map((f) => f.file);
	},

	isValid: function () {
		return this.uploadedFiles.length > 0;
	},

	destroy: function () {
		const $form = this.$el.closest('form');
		if ($form.length) {
			$form.off('submit.fileupload');
		}
		// Clean up object URLs
		this.uploadedFiles.forEach((fileData) => {
			if (fileData.url) {
				URL.revokeObjectURL(fileData.url);
			}
		});
		if (this.$lightbox) {
			this.$lightbox.remove();
		}
		this._super.apply(this, arguments);
	},
});
