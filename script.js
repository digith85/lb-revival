/* ============================================
   Lüthi und Blanc Revival Party — JavaScript
   Sparkle particles, calendar generation,
   form handling, scroll animations
   ============================================ */

(function () {
  'use strict';

  // ============================================
  // SPARKLE PARTICLE SYSTEM
  // ============================================
  const canvas = document.getElementById('sparkle-canvas');
  const ctx = canvas.getContext('2d');
  let particles = [];
  let animationId;

  function resizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  function createParticle() {
    return {
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      size: Math.random() * 2 + 0.5,
      speedY: -(Math.random() * 0.3 + 0.1),
      speedX: (Math.random() - 0.5) * 0.2,
      opacity: Math.random() * 0.6 + 0.2,
      twinkleSpeed: Math.random() * 0.02 + 0.005,
      twinkleOffset: Math.random() * Math.PI * 2,
      life: 0,
    };
  }

  function initParticles() {
    const count = Math.min(Math.floor(canvas.width * canvas.height / 12000), 120);
    particles = [];
    for (let i = 0; i < count; i++) {
      const p = createParticle();
      p.life = Math.random() * 400; // stagger initial positions
      particles.push(p);
    }
  }

  function updateParticles() {
    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x += p.speedX;
      p.y += p.speedY;
      p.life += 1;

      // Reset particle if it goes off screen
      if (p.y < -10 || p.x < -10 || p.x > canvas.width + 10) {
        particles[i] = createParticle();
        particles[i].y = canvas.height + 10;
      }
    }
  }

  function drawParticles() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (const p of particles) {
      const twinkle = Math.sin(p.life * p.twinkleSpeed + p.twinkleOffset);
      const alpha = p.opacity * (0.5 + 0.5 * twinkle);

      if (alpha <= 0.02) continue;

      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.fillStyle = '#ffffff';
      ctx.shadowBlur = p.size * 4;
      ctx.shadowColor = 'rgba(200, 210, 255, 0.6)';

      // Draw a small cross/star shape
      const s = p.size;
      ctx.beginPath();
      ctx.moveTo(p.x, p.y - s);
      ctx.lineTo(p.x + s * 0.3, p.y - s * 0.3);
      ctx.lineTo(p.x + s, p.y);
      ctx.lineTo(p.x + s * 0.3, p.y + s * 0.3);
      ctx.lineTo(p.x, p.y + s);
      ctx.lineTo(p.x - s * 0.3, p.y + s * 0.3);
      ctx.lineTo(p.x - s, p.y);
      ctx.lineTo(p.x - s * 0.3, p.y - s * 0.3);
      ctx.closePath();
      ctx.fill();

      ctx.restore();
    }
  }

  function animateParticles() {
    updateParticles();
    drawParticles();
    animationId = requestAnimationFrame(animateParticles);
  }

  // Check for reduced motion preference
  const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (!prefersReducedMotion) {
    resizeCanvas();
    initParticles();
    animateParticles();

    let resizeTimeout;
    window.addEventListener('resize', () => {
      clearTimeout(resizeTimeout);
      resizeTimeout = setTimeout(() => {
        resizeCanvas();
        initParticles();
      }, 200);
    });
  }


  // ============================================
  // SCROLL REVEAL ANIMATIONS
  // ============================================
  const revealElements = document.querySelectorAll('.reveal');

  if (!prefersReducedMotion && 'IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            // Stagger reveal for siblings
            const parent = entry.target.parentElement;
            const siblings = parent.querySelectorAll('.reveal');
            let delay = 0;

            siblings.forEach((el) => {
              if (el === entry.target || el.classList.contains('visible')) return;
            });

            entry.target.style.transitionDelay = '0.1s';
            entry.target.classList.add('visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.15, rootMargin: '0px 0px -40px 0px' }
    );

    revealElements.forEach((el) => observer.observe(el));
  } else {
    // If reduced motion or no IntersectionObserver, show everything
    revealElements.forEach((el) => el.classList.add('visible'));
  }


  // ============================================
  // CALENDAR GENERATION
  // ============================================
  const EVENT_CONFIG = {
    title: 'Revival Party — 20 Jahre Lüthi und Blanc',
    description:
      '20-Jahre-Jubiläum der Kultserie «Lüthi und Blanc» (1999–2007).\\nAlle ehemaligen Mitarbeitenden sind herzlich eingeladen!\\n\\nOrganisation: Janine Wille, Thierry Pool, Carla Hohmeister',
    location: 'Umgebung von Zürich (genauer Ort folgt)',
    // June 19, 2027 — 15:00–22:00 CEST
    dateStart: '20270619T130000Z',
    dateEnd: '20270619T200000Z',
    // Readable date for Google Calendar URL
    googleDates: '20270619T150000/20270619T220000',
  };

  /**
   * Generate an ICS calendar file content string
   */
  function generateICS() {
    const lines = [
      'BEGIN:VCALENDAR',
      'VERSION:2.0',
      'PRODID:-//Luethi und Blanc Revival//DE',
      'CALSCALE:GREGORIAN',
      'METHOD:PUBLISH',
      'BEGIN:VTIMEZONE',
      'TZID:Europe/Zurich',
      'BEGIN:DAYLIGHT',
      'DTSTART:19700329T020000',
      'RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=3',
      'TZOFFSETFROM:+0100',
      'TZOFFSETTO:+0200',
      'TZNAME:CEST',
      'END:DAYLIGHT',
      'BEGIN:STANDARD',
      'DTSTART:19701025T030000',
      'RRULE:FREQ=YEARLY;BYDAY=-1SU;BYMONTH=10',
      'TZOFFSETFROM:+0200',
      'TZOFFSETTO:+0100',
      'TZNAME:CET',
      'END:STANDARD',
      'END:VTIMEZONE',
      'BEGIN:VEVENT',
      'DTSTART;TZID=Europe/Zurich:20270619T150000',
      'DTEND;TZID=Europe/Zurich:20270619T220000',
      `SUMMARY:${EVENT_CONFIG.title}`,
      `DESCRIPTION:${EVENT_CONFIG.description.replace(/\\n/g, '\\n')}`,
      `LOCATION:${EVENT_CONFIG.location}`,
      'STATUS:CONFIRMED',
      `UID:luethi-blanc-revival-2027@revival-party.ch`,
      `DTSTAMP:${new Date().toISOString().replace(/[-:]/g, '').split('.')[0]}Z`,
      'END:VEVENT',
      'END:VCALENDAR',
    ];
    return lines.join('\r\n');
  }

  /**
   * Download a file with given content
   */
  function downloadFile(content, filename, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  }

  /**
   * Open Google Calendar event creation page
   */
  function openGoogleCalendar() {
    const params = new URLSearchParams({
      action: 'TEMPLATE',
      text: EVENT_CONFIG.title,
      dates: EVENT_CONFIG.googleDates,
      details: EVENT_CONFIG.description.replace(/\\n/g, '\n'),
      location: EVENT_CONFIG.location,
      ctz: 'Europe/Zurich',
    });
    window.open(`https://calendar.google.com/calendar/render?${params.toString()}`, '_blank');
  }

  // Calendar button event listeners
  document.getElementById('btn-ics-apple').addEventListener('click', () => {
    downloadFile(generateICS(), 'Luethi-und-Blanc-Revival-2027.ics', 'text/calendar;charset=utf-8');
  });

  document.getElementById('btn-google-calendar').addEventListener('click', () => {
    openGoogleCalendar();
  });

  document.getElementById('btn-ics-outlook').addEventListener('click', () => {
    downloadFile(generateICS(), 'Luethi-und-Blanc-Revival-2027.ics', 'text/calendar;charset=utf-8');
  });


  // ============================================
  // FORM HANDLING
  // ============================================
  const form = document.getElementById('interest-form');
  const formSuccess = document.getElementById('form-success');
  const btnSubmit = document.getElementById('btn-submit');

  const fields = {
    name: {
      input: document.getElementById('form-name'),
      error: document.getElementById('error-name'),
      validate: (val) => val.trim().length >= 2,
    },
    email: {
      input: document.getElementById('form-email'),
      error: document.getElementById('error-email'),
      validate: (val) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val.trim()),
    },
    department: {
      input: document.getElementById('form-department'),
      error: document.getElementById('error-department'),
      validate: (val) => val !== '',
    },
  };

  // Real-time validation: clear errors on input
  Object.values(fields).forEach(({ input, error }) => {
    input.addEventListener('input', () => {
      input.classList.remove('error');
      error.classList.remove('visible');
    });
    input.addEventListener('change', () => {
      input.classList.remove('error');
      error.classList.remove('visible');
    });
  });

  form.addEventListener('submit', (e) => {
    e.preventDefault();

    let isValid = true;

    // Validate all fields
    Object.entries(fields).forEach(([key, field]) => {
      const value = field.input.value;
      if (!field.validate(value)) {
        field.input.classList.add('error');
        field.error.classList.add('visible');
        isValid = false;
      } else {
        field.input.classList.remove('error');
        field.error.classList.remove('visible');
      }
    });

    if (!isValid) return;

    // Honeypot check: if a bot filled the hidden field, fake success silently
    const honeypot = document.getElementById('form-website');
    if (honeypot && honeypot.value) {
      form.style.display = 'none';
      formSuccess.classList.add('visible');
      return;
    }

    // Disable submit while "processing"
    btnSubmit.disabled = true;
    btnSubmit.textContent = 'Wird gesendet…';

    // Collect form data for Google Apps Script
    const formData = new URLSearchParams();
    formData.append('name', fields.name.input.value.trim());
    formData.append('email', fields.email.input.value.trim());
    formData.append('department', fields.department.input.value);
    formData.append('timestamp', new Date().toISOString());

    // Trage hier DEINE Google Apps Script Web App URL ein
    const GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbys6t_gQ8DV_3MSSQ7nOaKfqTgoCBqyIOB7RzmLnRZleiUTpwZ-sfhTPVX1gd58ye2WPQ/exec';

    // Fallback: If URL is not set yet, simulate success
    if (GOOGLE_SCRIPT_URL === 'DEINE_GOOGLE_SCRIPT_URL_HIER') {
      console.log('📋 Anmeldung erfasst (Simulation, URL fehlt):', Object.fromEntries(formData));
      setTimeout(() => {
        form.style.display = 'none';
        formSuccess.classList.add('visible');
      }, 800);
      return;
    }

    fetch(GOOGLE_SCRIPT_URL, {
      method: 'POST',
      body: formData,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      mode: 'no-cors'
    })
    .then(() => {
      form.style.display = 'none';
      formSuccess.classList.add('visible');
    })
    .catch(error => {
      console.error('Submission error!', error.message);
      alert('Es gab ein Problem beim Senden. Bitte versuche es später noch einmal.');
      btnSubmit.disabled = false;
      btnSubmit.textContent = 'Interesse anmelden';
    });
  });

  // ============================================
  // LEGAL MODALS (IMPRESSUM & DATENSCHUTZ)
  // ============================================
  const btnImpressum = document.getElementById('btn-impressum');
  const btnDatenschutz = document.getElementById('btn-datenschutz');
  const modalImpressum = document.getElementById('modal-impressum');
  const modalDatenschutz = document.getElementById('modal-datenschutz');
  const closeButtons = document.querySelectorAll('.modal-close');
  const overlays = document.querySelectorAll('.modal-overlay');

  function openModal(modal) {
    modal.classList.add('active');
    modal.setAttribute('aria-hidden', 'false');
    document.body.style.overflow = 'hidden'; // Prevent background scrolling
  }

  function closeModal(modal) {
    modal.classList.remove('active');
    modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = ''; // Restore scrolling
  }

  btnImpressum.addEventListener('click', () => openModal(modalImpressum));
  btnDatenschutz.addEventListener('click', () => openModal(modalDatenschutz));

  closeButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      const modal = e.target.closest('.modal-overlay');
      closeModal(modal);
    });
  });

  // Close modal when clicking outside of modal content
  overlays.forEach(overlay => {
    overlay.addEventListener('click', (e) => {
      if (e.target === overlay) {
        closeModal(overlay);
      }
    });
  });

  // Close modal on Escape key press
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      const activeModal = document.querySelector('.modal-overlay.active');
      if (activeModal) {
        closeModal(activeModal);
      }
    }
  });

})();
