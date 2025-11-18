import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";

export class BooleanSubscriber extends Component {
	static template = "realty_bds.SubscribeButton";
	static props = {
		id: { type: String, optional: true },
		record: { type: Object, optional: true },
		name: { type: String, optional: true },
		readonly: { type: Boolean, optional: true },
		invisible: { type: Boolean, optional: true },
	};
	static defaultProps = {
		readonly: false,
		invisible: false,
	};

	setup() {
		this.orm = useService("orm");
		this.state = useState({ loading: true, subscribed: false });
		onWillStart(async () => {
			await this._fetchInitial();
		});
	}

	get isUser() {
		return Boolean(this.props.record?.evalContext?.is_user);
	}

	get isSelf() {
		const recordId = Number(this.props.record?.resId || NaN);
		const currentPartnerId = Number(user.partnerId || NaN);
		return (
			Number.isFinite(recordId) &&
			Number.isFinite(currentPartnerId) &&
			recordId === currentPartnerId
		);
	}

	get titleStr() {
		return this.state.subscribed
			? "Unsubscribe from this partner"
			: "Subscribe to this partner";
	}


	_fetchInitial = async () => {
		const currentPartnerId = user.partnerId;
		if (!this.props.record || !currentPartnerId) {
			return;
		}
		const subscribedIds = this.props.record?.evalContext[this.props.name] || [];
		this.state.subscribed = subscribedIds.includes(currentPartnerId);
		this.state.loading = false;
	};

	toggleSubscribe = async () => {
		if (this.state.loading || this.props.readonly) return;
		this.state.loading = true;
		const targetPartner_id = this.props.record?.resId
		if (!targetPartner_id) return;
		try {
			const result = await this.orm.call(
				"res.partner",
				"action_toggle_subscribe",
				[[targetPartner_id]]
			);

			if (result && typeof result.subscribed !== "undefined") {
				this.state.subscribed = result.subscribed;
			}
		} catch (err) {
			console.error("BooleanSubscriber: toggle failed", err);
		} finally {
			this.state.loading = false;
		}
	};
}

export const BooleanSubscriberField = {
	component: BooleanSubscriber,
	supportedTypes: ["many2many"],
	isEmpty: () => true,
	extractProps: ({ attrs, fieldName }) => ({
		name: fieldName,
		readonly: attrs.readonly === "1" || attrs.readonly === "true",
		invisible: attrs.invisible === "1" || attrs.invisible === "true",
	}),
};

registry.category("fields").add("boolean_subscribe", BooleanSubscriberField);
