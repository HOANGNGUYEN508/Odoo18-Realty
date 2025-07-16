import { Component, useState } from "@odoo/owl";

export class PhotoLightbox extends Component {
  static template = "realty_bds.PhotoLightbox";
  static props = {
    files:             { type: Array },
    index:             { type: Number },
		presentationId:    { type: Number, optional: true },
    onClose:           { type: Function },
    onDelete:          { type: Function },
		onNavigate:        { type: Function },
		onSetPresentation: { type: Function }, 
  };

	setup() {
    this.state = useState({ loading: true });

  }

	onImageLoad() {
    this.state.loading = false;
  }

  get currentFile() {
		return this.props.files.find(file => file.id === this.props.index);
  }

	togglePresentation() {
    this.props.onSetPresentation(this.props.index);
  }

  get isPresentation() {
    return this.props.index === this.props.presentationId;
  }

  prev() {
    const len = this.props.files.length;
    const currentPos = this.props.files.findIndex(f => f.id === this.props.index);
    if (currentPos === -1) return;
    const prevPos = (currentPos + len - 1) % len;
    const prevId = this.props.files[prevPos].id;
    this.props.onNavigate?.(prevId);
  }

  next() {
    const len = this.props.files.length;
    const currentPos = this.props.files.findIndex(f => f.id === this.props.index);
    if (currentPos === -1) return;
    const nextPos = (currentPos + 1) % len;
    const nextId = this.props.files[nextPos].id;
    this.props.onNavigate?.(nextId);
  }

  close() {
    this.props.onClose();
  }

  async deleteCurrent() {
    this.state.loading = true;
		if (this.props.files.length > 1)
			this.next();
    try {
      await this.props.onDelete(this.props.index);
    } finally {
      this.state.loading = false;
    }
  }
}