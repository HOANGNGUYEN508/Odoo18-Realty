import {
	Component,
	useState,
	onWillStart,
	useEffect,
	useRef,
	onMounted,
	onWillUnmount,
} from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Many2ManyChip } from "./many2many_chip";
import { user } from "@web/core/user";
import { buildDomainFromValues, parseDomainToValues } from "./utils_filter";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class FilterDialog extends Component {
	static template = "realty_bds.FilterDialog";
	static components = { Dialog, Many2ManyChip };

	setup() {
		// super.setup();
		this.orm = useService("orm");
		this.dialogService = useService("dialog");

		// SINGLE ref for the entire dropdown wrapper (toggle + menu)
		this.containerRef = useRef("prefContainer");

		const toStr = (v) => (v != null ? String(v) : "");
		const initial = this.props.initialState || {};
		this.values = useState({
			province_id: toStr(initial.province_id),
			district_id: toStr(initial.district_id),
			commune_id: toStr(initial.commune_id),
			region_id: toStr(initial.region_id),
			status_id: toStr(initial.status_id),
			type_id: toStr(initial.type_id),
			land_tittle_id: toStr(initial.land_tittle_id),
			feature_ids: Array.isArray(initial.feature_ids)
				? initial.feature_ids
				: [],
			min_price: toStr(initial.min_price),
			max_price: toStr(initial.max_price),
			unit_price_min_id: toStr(initial.unit_price_min_id),
			unit_price_max_id: toStr(initial.unit_price_max_id),
			preference_id: toStr(initial.preference_id),
			name: toStr(initial.name),
			is_default: initial.is_default,
		});

		this.save = useState({
			name: "",
			is_default: "",
		});
		this.savedFilters = useState({ list: [] });

		this.options = useState({
			regions: [],
			provinces: [],
			districts: [],
			communes: [],
			types: [],
			land_tittles: [],
			unit_price_units: [],
			features: [],
			statuss: [],
		});
		this.loading = useState({ active: false });

		this.state = useState({
			activeIndex: 0,
			dropdownOpen: false,
		});

		this.handleFeaturesOptions = (allOptions) => {
			this.options.features = allOptions;
		};

		// ─── Outside-click handler ───
		const handleClickOutside = (event) => {
			if (
				this.state.dropdownOpen &&
				this.containerRef.el &&
				!this.containerRef.el.contains(event.target)
			)
				this.closePreferenceDropdown();
		};

		onMounted(() => {
			document.addEventListener("mousedown", handleClickOutside);
		});
		onWillUnmount(() => {
			document.removeEventListener("mousedown", handleClickOutside);
		});

		onWillStart(async () => {
			this.loading.active = true;
			try {
				// 1) Get Vietnam’s country ID
				const [vnCountry] = await this.orm.call("res.country", "search_read", [
					[["code", "=", "VN"]], // or ["name", "=", "Vietnam"]
					["id"],
				]);
				const vnId = vnCountry?.id;

				// 2) Define the models, their option keys, and which fields to load
				const models = [
					["region", "regions", ["id", "name"]],
					["res.country.state", "provinces", ["id", "name", "country_id"]],
					["district", "districts", ["id", "name", "province_id"]],
					["commune", "communes", ["id", "name", "district_id"]],
					["type", "types", ["id", "name"]],
					["land_tittle", "land_tittles", ["id", "name"]],
					["unit_price", "unit_prices", ["id", "name", "multiplier"]],
					["status", "statuss", ["id", "name"]],
				];

				// 3) Build a parallel array of domains
				const baseDomain = [["active", "=", true]];
				const domains = models.map(([model]) => {
					if (model === "res.country.state" && vnId) {
						// Only states in Vietnam
						return [...baseDomain, ["country_id", "=", vnId]];
					}
					return baseDomain;
				});

				// 4) Fetch all option lists in parallel
				const results = await Promise.all(
					models.map(([model, , fields], idx) =>
						this.orm.call(model, "search_read", [domains[idx], fields])
					)
				);

				// 5) Merge with your “Select …” placeholders
				const labels = {
					regions: "Select Region",
					provinces: "Select Province",
					districts: "Select District",
					communes: "Select Commune",
					types: "Select Type",
					land_tittles: "Select Title",
					unit_prices: "Select Unit Price",
					statuss: "Select Status",
				};
				models.forEach(([, key], idx) => {
					this.options[key] = [{ id: "", name: labels[key] }, ...results[idx]];
				});

				// 6) Load any saved filters as before
				await this.loadSavedFilters();
			} finally {
				this.loading.active = false;
			}
		});

		useEffect(
			() => {
				if (!this.values.min_price) {
					this.values.unit_price_min_id = "";
				}
			},
			() => [this.values.min_price]
		);
		useEffect(
			() => {
				if (!this.values.max_price) {
					this.values.unit_price_max_id = "";
				}
			},
			() => [this.values.max_price]
		);
	}

	validatePrices() {
		const { min_price, max_price, unit_price_min_id, unit_price_max_id } = this.values;
		if (min_price && !unit_price_min_id)
			return alert("Please select a unit for Min Price");
		if (max_price && !unit_price_max_id)
			return alert("Please select a unit for Max Price");
		if (min_price && max_price && parseFloat(min_price) > parseFloat(max_price))
			return alert("Maximum price must be ≥ Minimum price");
		return true;
	}

	onProvinceChange() {
		Object.assign(this.values, {
			district_id: "",
			commune_id: "",
		});
	}
	onDistrictChange() {
		this.values.commune_id = "";
	}

	closePreferenceDropdown() {
		Object.assign(this.state, {
			dropdownOpen: false,
			activeIndex: 0,
		});
	}

	onPreferenceDropdownFocus() {
		Object.assign(this.state, {
			dropdownOpen: true,
			activeIndex: 0,
		});
	}

	async loadSavedFilters() {
		const saved = await this.orm.searchRead(
			"ir.filters",
			[
				["model_id", "=", "product.template"],
				["user_id", "=", user.userId],
			],
			["id", "name", "is_default"]
		);
		this.savedFilters.list = saved;
	}

	onDeletePreferenceClick(filterId) {
		this.dialogService.add(ConfirmationDialog, {
			title: "Confirm Deletion",
			body: "Are you sure you want to delete this preference?",
			confirmLabel: "Delete",
			confirm: async () => {
				try {
					await this.orm.call("ir.filters", "unlink", [[filterId]]);
					this.env.services.notification.add("Preference deleted", {
						type: "success",
					});
					if (String(filterId) === this.values.preference_id) {
						this.values.preference_id = "";
					}
					await this.loadSavedFilters();
				} catch (e) {
					this.env.services.dialog.alert(
						"An error occurred while deleting the preference."
					);
				}
			},
			cancel: () => {},
		});
	}

	async selectPreference(filterId) {
		if (!filterId) {
			this.values.preference_id = "";
			this.closePreferenceDropdown();
			return;
		}

		try {
			const [record] = await this.orm.read(
				"ir.filters",
				[filterId],
				["name", "domain", "context", "is_default"]
			);

			if (!record) return;

			const parsedValues = parseDomainToValues(record.domain, record.context);

			Object.assign(this.values, {
				...parsedValues,
				preference_id: String(filterId),
				name: record.name,
				is_default: record.is_default,
			});

			await this.props.applyFilter({ ...this.values }, { ...this.options });
			this.props.close();
		} catch (err) {
			this.env.services.dialog.alert("Failed to select preference:", err);
		}
	}

	async onPreferenceSearchKeydown(ev) {
		const realList = this.savedFilters.list || [];
		const totalLength = realList.length + 1; // +1 for “No Preference” row

		const moveUp = () => {
			this.state.activeIndex =
				(this.state.activeIndex - 1 + totalLength) % totalLength;
		};
		const moveDown = () => {
			this.state.activeIndex = (this.state.activeIndex + 1) % totalLength;
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
				if (this.state.activeIndex === 0) {
					await this.selectPreference(null);
				} else {
					const chosen = realList[this.state.activeIndex - 1];
					if (chosen) {
						await this.selectPreference(chosen.id);
					}
				}
				break;
			case "Escape":
				this.closePreferenceDropdown();
				break;
		}

		if (["ArrowDown", "ArrowUp", "ArrowLeft", "ArrowRight"].includes(ev.key)) {
			window.requestAnimationFrame(() => {
				// Use the same containerRef to find the <li> elements
				const allItems = Array.from(
					this.containerRef.el.querySelectorAll(".preference-menu li")
				);
				const activeEl = allItems[this.state.activeIndex];
				activeEl?.scrollIntoView({ block: "nearest" });
			});
		}
	}

	async onSaveFilterClick() {
		if (!this.save.name) {
			this.env.services.dialog.alert("Please provide a name for the filter.");
			return;
		}

		if (!this.validatePrices()) return;

		const domain = buildDomainFromValues(this.values, this.options);
		const filterData = {
			name: this.save.name,
			model_id: "product.template",
			context: {
				domain,
				min_price: this.values.min_price,
				max_price: this.values.max_price,
				unit_price_min_id: this.values.unit_price_min_id,
				unit_price_max_id: this.values.unit_price_max_id,
			},
			is_default: this.save.is_default,
		};

		await this.orm.call("ir.filters", "save_or_override_filter", [filterData]);
		this.env.services.notification.add("Filter saved", { type: "success" });
		Object.assign(this.save, {
			name: "",
			is_default: "",
		});
		await this.loadSavedFilters();
	}

	async onApplyButtonClick() {
		if (!this.validatePrices()) return;
		Object.assign(this.values, {
			preference_id: "",
			name: "",
			is_default: false,
		});
		await this.props.applyFilter({ ...this.values }, { ...this.options });
		this.props.close();
	}

	async onResetButtonClick() {
		await this.props.applyFilter();
		this.props.close();
	}

	get savedFiltersWithIndex() {
		return this.savedFilters.list.map((opt, i) => ({ opt, i }));
	}
}
