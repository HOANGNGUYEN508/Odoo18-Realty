import { registry } from "@web/core/registry";
import { RealtyCommentDialog } from "./realty_comment_dialog";

export function RealtyCommentDialogAction(env, action) {
    const params = action.params || {};
    
    const dialogParams = {
        res_model: params.res_model ?? null,
        res_id: params.res_id != null ? Number(params.res_id) : null,
				group: params.group || {},
    };

    env.services.dialog.add(RealtyCommentDialog, {
        params: dialogParams,
        close: () => env.services.dialog.remove(),
    });
}

registry.category("actions").add("realty_comment_dialog_action", RealtyCommentDialogAction);
