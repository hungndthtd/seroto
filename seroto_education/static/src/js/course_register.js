console.log("Seroto Education JS: Initialized");

document.addEventListener('click', function(ev) {
    const btn = ev.target.closest('.btn-register-now');
    if (btn) {
        ev.preventDefault();
        console.log("Seroto Education JS: Register button clicked", btn);
        const courseId = btn.getAttribute('data-course-id');
        const courseName = btn.getAttribute('data-course-name');
        
        const modalElement = document.getElementById('serotoRegisterModal');
        if (modalElement) {
            document.getElementById('reg-course-id').value = courseId;
            document.getElementById('reg-course-name').value = courseName;
            
            // Show bootstrap modal via hidden trigger button (create dynamically if missing)
            let triggerBtn = document.getElementById('triggerSerotoRegisterModal');
            if (!triggerBtn) {
                console.log("Seroto Education JS: Creating trigger button dynamically");
                triggerBtn = document.createElement('button');
                triggerBtn.id = 'triggerSerotoRegisterModal';
                triggerBtn.className = 'd-none';
                triggerBtn.setAttribute('data-bs-toggle', 'modal');
                triggerBtn.setAttribute('data-bs-target', '#serotoRegisterModal');
                document.body.appendChild(triggerBtn);
            }
            
            triggerBtn.click();
            console.log("Seroto Education JS: Modal trigger button clicked");
        } else {
            console.error("Seroto Education JS: Modal element #serotoRegisterModal not found!");
        }
    }
});

document.addEventListener('submit', function(ev) {
    const form = ev.target.closest('#seroto-register-form');
    if (form) {
        ev.preventDefault();
        console.log("Seroto Education JS: Form submitted");
        const submitBtn = form.querySelector('button[type="submit"]');
        const courseId = document.getElementById('reg-course-id').value;
        const name = document.getElementById('reg-name').value;
        const phone = document.getElementById('reg-phone').value;
        const email = document.getElementById('reg-email').value;
        // Honeypot check
        const honeypotVal = document.getElementById('reg-website') ? document.getElementById('reg-website').value : "";

        // Frontend Rate-limiting: Prevent submission for the same course in under 2 minutes
        const lastRegTime = localStorage.getItem('seroto_reg_time_' + courseId);
        const now = Date.now();
        if (lastRegTime && (now - parseInt(lastRegTime)) < 120000) { // 2 minutes (120,000 ms)
            alert('Bạn đã gửi yêu cầu đăng ký khóa học này gần đây. Vui lòng đợi 2 phút trước khi gửi lại!');
            return;
        }

        // Disable submit button
        submitBtn.disabled = true;
        const oldText = submitBtn.innerText;
        submitBtn.innerText = 'Đang gửi đăng ký...';

        fetch('/course/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                jsonrpc: '2.0',
                method: 'call',
                params: {
                    course_id: courseId,
                    name: name,
                    phone: phone,
                    email: email,
                    website: honeypotVal
                }
            })
        })
        .then(response => response.json())
        .then(data => {
            console.log("Seroto Education JS: Response received", data);
            const result = data.result || {};
            if (result.success) {
                // Store registration time
                localStorage.setItem('seroto_reg_time_' + courseId, Date.now());

                // Find or dynamically create success screen (handles old saved page HTML cache)
                let successDiv = document.getElementById('seroto-register-success');
                if (!successDiv) {
                    console.log("Seroto Education JS: Creating success div dynamically");
                    successDiv = document.createElement('div');
                    successDiv.id = 'seroto-register-success';
                    successDiv.className = 'text-center py-4';
                    successDiv.innerHTML = `
                        <div class="mb-3">
                            <i class="fa fa-check-circle text-success" style="font-size: 4.5rem;"></i>
                        </div>
                        <h4 class="fw-bold text-dark mb-2">Đăng ký thành công!</h4>
                        <p class="text-muted mb-4" id="success-message-text">${result.message}</p>
                        <button type="button" class="btn btn-primary px-4 py-2 rounded-3 fw-bold" data-bs-dismiss="modal">Đồng ý</button>
                    `;
                    form.parentNode.appendChild(successDiv);
                } else {
                    const successText = document.getElementById('success-message-text');
                    if (successText) {
                        successText.innerText = result.message;
                    }
                }
                form.classList.add('d-none');
                successDiv.classList.remove('d-none');
            } else {
                alert(result.message || 'Có lỗi xảy ra, vui lòng thử lại.');
            }
            submitBtn.disabled = false;
            submitBtn.innerText = oldText;
        })
        .catch(function (err) {
            console.error("Seroto Education JS: Error submitting form", err);
            alert('Lỗi kết nối hệ thống. Vui lòng thử lại sau.');
            submitBtn.disabled = false;
            submitBtn.innerText = oldText;
        });
    }
});

// Reset modal to show form when modal is closed
document.addEventListener('hidden.bs.modal', function (ev) {
    if (ev.target.id === 'serotoRegisterModal') {
        console.log("Seroto Education JS: Modal closed, resetting form state");
        const form = document.getElementById('seroto-register-form');
        const successDiv = document.getElementById('seroto-register-success');
        if (form && successDiv) {
            form.classList.remove('d-none');
            successDiv.classList.add('d-none');
            form.reset();
        }
    }
});

