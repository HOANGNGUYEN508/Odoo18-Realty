import { KanbanController } from "@web/views/kanban/kanban_controller";
import { kanbanView } from '@web/views/kanban/kanban_view';
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { GuidelineDialog } from "./guideline_dialog";

export class GuidelineController extends KanbanController {
	static components = {
		...KanbanController.components,
		GuidelineDialog,
	};

	setup() {
		super.setup();
		this.dialog = useService("dialog");
	}

	openGuidelineDialog() {
		this.dialog.add(GuidelineDialog, {
			title: "Moderator Guidelines",
			close: () => this.dialog.remove(),
		});
	}
}

export const customKanbanController = {
	...kanbanView,
	Controller: GuidelineController,
}

registry.category("views").add("info_kanban", customKanbanController);
