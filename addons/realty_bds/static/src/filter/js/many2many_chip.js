import { Component, useState, onWillStart, onMounted, onWillUnmount, useRef } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";

// Global cache, keyed by relationModel
const globalCache = {};

export class Many2ManyChip extends Component {
	static template = "realty_bds.Many2ManyChip";

	static props = {
    name: { type: String, optional: true },
    readonly: { type: Boolean, optional: true },
    record: { type: Object, optional: true  },
		relationModel: { type: String, optional: true },
		value: { type: Array, optional: true },
		update: { type: Function, optional: true },
		onOptionsLoaded: { type: Function, optional: true },
		maxVisible: { type: Number, optional: true },
		rowsPerColumn: { type: Number, optional: true },
	};

	static defaultProps = {
		value: [],
		readonly: true,
		maxVisible: 3,
		rowsPerColumn: 8,
	};

	setup() {
		super.setup();
		this.orm = useService("orm");
		this.maxVisible = this.props.maxVisible;

		let fieldDef;
    let currentIds = [];

		if (this.props.name && this.props.record) {
			fieldDef = this.props.record.fields[this.props.name];
			currentIds = this.props.record.evalContext[this.props.name];
		}

		this.state = useState({
			allOptions: [], 
			selectedIds: new Set(
				(Array.isArray(this.props.value) && this.props.value.length) ? this.props.value : currentIds
			),
			search: "", 
			activeIndex: -1, 
			dropdownOpen: false,
			loaded: false,
		});

		// refs for click-outside and input focus
		this.rootRef = useRef("root");
		this.searchRef = useRef("searchInput");

		onWillStart(async () => {
			const model = this.props.relationModel || fieldDef.relation;
			if (!globalCache[model]) {
				const recs = await this.orm.searchRead(
					model,
					[["active", "=", true]],
					["id", "name"]
				);
				globalCache[model] = Array.isArray(recs) ? recs : [];
			}
			Object.assign(this.state, {
				allOptions: globalCache[model],
				loaded: true,
			});
			if (this.props.onOptionsLoaded) {
				this.props.onOptionsLoaded(this.state.allOptions);
			}
		});

		const handleClickOutside = (event) => {
			if (this.rootRef.el && !this.rootRef.el.contains(event.target)) {
				this.state.dropdownOpen = false;
			}
		};
		onMounted(() => {
			document.addEventListener("click", handleClickOutside);
		});
		onWillUnmount(() => {
			document.removeEventListener("click", handleClickOutside);
		});

		this.onInputFocus = () => {
			this.state.dropdownOpen = true;
			this.state.activeIndex = 0;
			window.requestAnimationFrame(() => {
				const active = document.querySelector(".list-group-item.focused");
				active?.scrollIntoView({ block: "nearest" });
			});
		};
	}

	get selectedChips() {
		return this.state.allOptions.filter((o) =>
			this.state.selectedIds.has(o.id)
		);
	}

	get visibleChips() {
		return this.selectedChips.slice(0, this.maxVisible);
	}

	get hiddenCount() {
		return Math.max(0, this.selectedChips.length - this.maxVisible);
	}

	// Now show *all* matching options, not excluding selected ones
	get filteredOptions() {
		const term = this.state.search.trim().toLowerCase();
		const list = this.state.allOptions;
		if (!term) {
			return list;
		}
		return list.filter((o) => o.name.toLowerCase().includes(term));
	}

	get filteredWithIndex() {
		return this.filteredOptions.map((opt, i) => ({ opt, i }));
	}

	removeChip(id) {
		if (!this.state.selectedIds.has(id)) return;
		this.state.selectedIds.delete(id);
		this._notifyParent();
	}

	toggleOption(id) {
		if (this.state.selectedIds.has(id)) {
			this.state.selectedIds.delete(id);
		} else {
			this.state.selectedIds.add(id);
		}
		// clear search so user sees full list again
		this.state.search = "";
		this._notifyParent();
	}

	onSearchKeydown(ev) {
		const len = this.filteredOptions.length;
		if (!len) return;

		const moveUp = () => {
			this.state.activeIndex = (this.state.activeIndex - 1 + len) % len;
		};
		const moveDown = () => {
			this.state.activeIndex = (this.state.activeIndex + 1) % len;
		};

		switch (ev.key) {
			case "ArrowDown":
			case "ArrowRight":
				ev.preventDefault();
				moveDown();
				break;
			case "ArrowUp":
			case "ArrowLeft":
				ev.preventDefault();
				moveUp();
				break;
			case "Enter":
				ev.preventDefault();
				const opt = this.filteredOptions[this.state.activeIndex];
				if (opt) {
					this.toggleOption(opt.id);
				}
				break;
			case "Escape":
				this.state.search = "";
				this.state.activeIndex = 0;
				break;
		}

		if (["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"].includes(ev.key)) {
			window.requestAnimationFrame(() => {
				const active = document.querySelector(".list-group-item.focused");
				active?.scrollIntoView({ block: "nearest" });
			});
		}
	}

	_notifyParent() {
		const ids = [...this.state.selectedIds];
		if (this.props.update) {
			this.props.update(ids);
		} else {
			this.trigger("field_changed", { value: ids, valid: true });
		}
	}

	willUpdateProps(nextProps) {
		const newIds = Array.isArray(nextProps.value) ? nextProps.value : [];
		const nextSet = new Set(newIds);
		const curr = [...this.state.selectedIds].sort().toString();
		const nextStr = [...nextSet].sort().toString();
		if (curr !== nextStr) {
			this.state.selectedIds = nextSet;
		}
	}

	get chipColumns() {
    const names = this.selectedChips.map(c => c.name);
    const cols = [];
    for (let i = 0; i < names.length; i += this.props.rowsPerColumn) {
      cols.push(names.slice(i, i + this.props.rowsPerColumn));
    }
    return cols;
  }

  get columnCount() {
    return this.chipColumns.length;
  }

	get tooltipInfo() {
		if (this.selectedChips.length === 0) {
    	return null; 
  	}
		return JSON.stringify({
			items: this.selectedChips.map(c => c.name),
			columnCount: this.columnCount,
		});
	}
}

export const Many2ManyChipField = {
  component: Many2ManyChip,
  displayName: "Many2Many Chips",
  supportedTypes: ["many2many"],
  extractProps({ attrs, options, string }, dynamicInfo) {
    return {
			maxVisible: options.maxVisible || 3,
			rowsPerColumn: options.rowsPerColumn || 8,
    };
  },
};

registry.category("fields").add("many2many_chip", Many2ManyChipField);