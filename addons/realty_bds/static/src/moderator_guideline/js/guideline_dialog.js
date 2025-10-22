import { Dialog } from "@web/core/dialog/dialog";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart } from "@odoo/owl";

// Global cache object
const globalCache = {};

export class GuidelineDialog extends Component {
	static template = "realty_bds.GuidelineDialog";
	static components = { Dialog };

	setup() {
		this.orm = useService("orm");
		this.loading = useState({ active: false });
		this.values = useState({ list: [] });

		onWillStart(async () => {
			this.loading.active = true;

			// Cache key for guidelines
			const cacheKey = "moderator_guideline_active";

			try {
				// Check if data exists in cache
				if (globalCache[cacheKey]) {
					this.values.list = globalCache[cacheKey];
				} else {
					// Fetch from server if not in cache
					const guidelines = await this.orm.searchRead(
						"moderator_guideline",
						[["active", "=", true]],
						["id", "name"],
						{ order: "id" }
					);

					// Store in cache
					globalCache[cacheKey] = guidelines;
					this.values.list = guidelines;
				}
			} catch (error) {
				console.error("Error loading guidelines:", error);
				this.values.list = [];
			} finally {
				this.loading.active = false;
			}
		});
	}
}
