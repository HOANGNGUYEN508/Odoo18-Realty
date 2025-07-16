/** @odoo-module **/
import publicWidget from "@web/legacy/js/public/public_widget";
import { registry } from "@web/core/registry";

async function notify_this() {
  console.log("Hey ya")
  var myService = {
    dependencies: ["notification"],
    start(env, { notification }) {
      notification.add("Im here", {
        type: 'success',
      }
    );
  }
}; 
  return registry.category("services").add("myService", myService)
}

publicWidget.registry.NotifyOnChange = publicWidget.Widget.extend({
  selector: '.my_notify_marker[data-notify="true"]',
  start() {
    // fires once for each matching element
    notify_this();
    return this._super(...arguments);
  },
});
