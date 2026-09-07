# -*- coding: utf-8 -*-

from . import academic_course
from . import academic_course_pricing
from . import academic_course_question
from . import academic_course_audience
from . import academic_intake
from . import academic_class
from . import academic_session
from . import academic_enrollment
from . import academic_attendance
from . import academic_certificate
from . import sale_order
from . import crm_lead
from . import academic_ip_log
from . import account_move
from . import product_template
# academic_report_metric tạo SQL View tham chiếu cột account_move_line.class_id
# (khai báo trong account_move.py ở trên) và product_template.is_donation_product
# (khai báo trong product_template.py ở trên) - PHẢI nạp sau 2 file đó, không thì cột
# chưa kịp tạo trong database lúc View được dựng, gây lỗi "column does not exist".
from . import academic_report_metric
from . import res_partner
from . import website
