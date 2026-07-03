/* ============================================================
   Seroto Education – Website Registration JS
   Multi-step form navigation + AJAX class loader
   ============================================================ */

function seInitRegistrationForm() {

    // ── Multi-step form ────────────────────────────────────────
    const steps    = document.querySelectorAll('.se-step');
    const sections = document.querySelectorAll('.se-form-section');
    const btnNext  = document.querySelectorAll('.se-btn-next');
    const btnPrev  = document.querySelectorAll('.se-btn-prev');
    let currentStep = 0;

    function goToStep(n) {
        steps.forEach((s, i) => {
            s.classList.remove('active', 'done');
            if (i < n) s.classList.add('done');
            if (i === n) s.classList.add('active');
        });
        sections.forEach((s, i) => {
            s.classList.toggle('active', i === n);
        });
        currentStep = n;
        // Scroll lên đầu form
        const formCard = document.querySelector('.se-form-card');
        if (formCard) formCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function validateSection(n) {
        const section = sections[n];
        if (!section) return true;
        let valid = true;
        section.querySelectorAll('[required]').forEach(function (el) {
            el.classList.remove('se-invalid');
            if (!el.value.trim()) {
                el.classList.add('se-invalid');
                el.style.borderColor = 'var(--se-error)';
                valid = false;
            } else {
                el.style.borderColor = '';
            }
        });
        if (!valid) {
            const first = section.querySelector('.se-invalid');
            if (first) first.focus();
        }
        return valid;
    }

    btnNext.forEach(function (btn) {
        btn.addEventListener('click', function () {
            if (validateSection(currentStep)) {
                goToStep(currentStep + 1);
            }
        });
    });
    btnPrev.forEach(function (btn) {
        btn.addEventListener('click', function () {
            goToStep(currentStep - 1);
        });
    });
    steps.forEach(function (step, i) {
        step.addEventListener('click', function () {
            // Chỉ cho phép click vào step đã done
            if (step.classList.contains('done')) goToStep(i);
        });
    });

    // Init
    if (sections.length > 0) goToStep(0);

    // ── AJAX: Load classes khi chọn khoá học ──────────────────
    const courseSelect = document.getElementById('course_id');
    const classContainer = document.getElementById('se-class-container');
    const classHiddenInput = document.getElementById('class_id');

    if (courseSelect && classContainer) {
        courseSelect.addEventListener('change', function () {
            const courseId = this.value;
            classContainer.innerHTML = '<p class="text-muted" style="font-size:14px;">Đang tải lịch học…</p>';
            if (classHiddenInput) classHiddenInput.value = '';

            if (!courseId) {
                classContainer.innerHTML = '';
                return;
            }

            fetch('/dang-ky/get-classes', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({ jsonrpc: '2.0', method: 'call', params: { course_id: parseInt(courseId) } }),
            })
            .then(r => r.json())
            .then(data => {
                const classes = data.result && data.result.classes ? data.result.classes : [];
                if (classes.length === 0) {
                    classContainer.innerHTML = '<p class="text-muted" style="font-size:14px;">Hiện chưa có lịch học. Chúng tôi sẽ liên hệ tư vấn lịch phù hợp.</p>';
                    return;
                }
                let html = '<div class="se-class-options">';
                classes.forEach(function (c, idx) {
                    const seatLabel = c.available_seats <= 3 ? 'Sắp đầy' : 'Còn chỗ';
                    const seatClass = c.available_seats <= 3 ? 'few' : '';
                    html += `
                    <div class="se-class-card" onclick="selectClass(this, ${c.id})">
                        <input type="radio" name="_class_radio" value="${c.id}" ${idx===0?'checked':''}>
                        <span class="se-class-badge ${seatClass}">${seatLabel} (${c.available_seats})</span>
                        <div class="se-class-name">${c.name}</div>
                        <div class="se-class-detail">
                            📅 Khai giảng: ${c.date_start || 'Sắp thông báo'}
                            ${c.schedule ? ' &nbsp;·&nbsp; 🕐 ' + c.schedule : ''}
                            ${c.teacher ? ' &nbsp;·&nbsp; 👩‍🏫 ' + c.teacher : ''}
                        </div>
                    </div>`;
                });
                html += '</div>';
                classContainer.innerHTML = html;
                // Auto-select đầu tiên
                if (classHiddenInput && classes.length > 0) {
                    classHiddenInput.value = classes[0].id;
                }
            })
            .catch(function () {
                classContainer.innerHTML = '<p style="color:var(--se-error);font-size:14px;">Không tải được lịch học. Vui lòng thử lại.</p>';
            });
        });
    }

    // ── Parent section toggle ──────────────────────────────────
    const toggleParent = document.getElementById('se-toggle-parent');
    const parentSection = document.getElementById('se-parent-section');
    if (toggleParent && parentSection) {
        toggleParent.addEventListener('change', function () {
            parentSection.style.display = this.checked ? 'block' : 'none';
        });
    }

    // ── Character counter cho textarea ────────────────────────
    document.querySelectorAll('textarea[maxlength]').forEach(function (ta) {
        const counter = document.createElement('div');
        counter.className = 'se-hint';
        counter.style.textAlign = 'right';
        ta.parentNode.appendChild(counter);
        function update() {
            counter.textContent = ta.value.length + ' / ' + ta.getAttribute('maxlength');
        }
        ta.addEventListener('input', update);
        update();
    });

    // ── Số điện thoại: chỉ cho nhập số và dấu cộng ───────────
    document.querySelectorAll('input[type=tel]').forEach(function (el) {
        el.addEventListener('input', function () {
            this.value = this.value.replace(/[^0-9+\-\s]/g, '');
        });
    });

    // ── Hiệu ứng fade-in cho thẻ khoá học ────────────────────
    const cards = document.querySelectorAll('.se-course-card');
    if ('IntersectionObserver' in window) {
        const observer = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.style.opacity = '1';
                    entry.target.style.transform = 'translateY(0)';
                }
            });
        }, { threshold: 0.1 });
        cards.forEach(function (card) {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            card.style.transition = 'opacity .4s ease, transform .4s ease';
            observer.observe(card);
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', seInitRegistrationForm);
} else {
    // Bundle JS có thể tải dạng async và chạy sau khi DOMContentLoaded
    // đã bắn xong (HTML render từ server nên DOM đã sẵn sàng) → chạy ngay.
    seInitRegistrationForm();
}

// Global function cho class card click
function selectClass(el, classId) {
    document.querySelectorAll('.se-class-card').forEach(function (c) {
        c.classList.remove('selected');
    });
    el.classList.add('selected');
    const radio = el.querySelector('input[type=radio]');
    if (radio) radio.checked = true;
    const hidden = document.getElementById('class_id');
    if (hidden) hidden.value = classId;
}
