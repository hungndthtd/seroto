/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.CourseRegister = publicWidget.Widget.extend({

    selector: "#wrap",

    events: {
        "click .register-course": "_onRegisterClick",
    },

    start() {
        console.log("Widget Started");
        return this._super(...arguments);
    },

    _onRegisterClick(ev) {
        ev.preventDefault();

        console.log("Click");

        console.log(ev.currentTarget.dataset.course);
    },

});