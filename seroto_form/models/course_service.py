from odoo import models


class CourseService(models.AbstractModel):
    _name = "seroto.course.service"
    _description = "Course Service"

    def get_home_courses(self, limit=3):

        category = self.env["product.category"].search(
            [
                ("name", "=", "Khóa học")
            ],
            limit=1,
        )

        domain = [
            ("sale_ok", "=", True),
            ("active", "=", True),
        ]

        if category:
            domain.append(("categ_id", "=", category.id))

        return self.env["product.template"].search(
            domain,
            limit=limit,
            order="id desc",
        )