// /** @odoo-module **/

// import publicWidget from "@web/legacy/js/public/public_widget";

// publicWidget.registry.EventRegisterList = publicWidget.Widget.extend({
//     selector: ".course-register-btn",

//     events: {
//         click: "_onClickRegister",
//     },

//     _onClickRegister(ev) {
//         ev.preventDefault();

//         const eventId = this.$el.data("event-id");

//         // tìm node gốc Odoo nếu tồn tại
//         const $target = $(`.o_wevent_registration_btn[data-event-id='${eventId}']`);

//         if ($target.length) {
//             $target.trigger("click");
//         } else {
//             console.warn("Odoo register button not found in DOM");
//         }
//     },
// });