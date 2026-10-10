window.adminEscapeHTML = value => String(value ?? '').replace(/[&<>"']/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[character]));

/* Shared workspace navigation; authentication stays in the existing page clients. */
document.addEventListener('DOMContentLoaded', () => {
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('overlay');
  const menu = document.getElementById('admin-menu');
  if (!sidebar) return;
  const mobile = window.matchMedia('(max-width: 900px)');

  window.toggleSidebar = (open = !sidebar.classList.contains('is-open')) => {
    const visible = mobile.matches && open;
    sidebar.classList.toggle('is-open', visible);
    sidebar.inert = mobile.matches && !visible;
    overlay.classList.toggle('hidden', !visible);
    menu.setAttribute('aria-expanded', String(visible));
    document.body.classList.toggle('drawer-open', visible);
    if (visible) sidebar.querySelector('.sidebar-close').focus();
    else if (mobile.matches) menu.focus();
  };
  sidebar.inert = mobile.matches;
  mobile.addEventListener('change', () => window.toggleSidebar(false));
  document.addEventListener('keydown', event => {
    if (!mobile.matches || !sidebar.classList.contains('is-open')) return;
    if (event.key === 'Escape') window.toggleSidebar(false);
    if (event.key !== 'Tab') return;
    const items = [...sidebar.querySelectorAll('a[href], button')].filter(el => el.offsetParent !== null);
    const first = items[0], last = items[items.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault(); last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault(); first.focus();
    }
  });
  window.logout = () => {
    localStorage.removeItem('wvc_admin_token');
    window.location.href = '/admin/login';
  };
});

document.addEventListener('DOMContentLoaded', () => {
  const focusable = root => [...root.querySelectorAll('a[href], button, input, select, textarea, [tabindex="0"]')].filter(el => !el.disabled && el.getClientRects().length);
  let activeDialog = null;
  let returnFocus = null;
  const dialogs = [...document.querySelectorAll('[role="dialog"]')];
  dialogs.forEach(dialog => {
    new MutationObserver(() => {
      if (!dialog.classList.contains('hidden')) {
        if (activeDialog !== dialog) {
          returnFocus = document.activeElement;
          activeDialog = dialog;
          focusable(dialog)[0]?.focus();
        }
      } else if (activeDialog === dialog) {
        activeDialog = null;
        returnFocus?.focus();
      }
    }).observe(dialog, { attributes: true, attributeFilter: ['class'] });
  });
  document.addEventListener('keydown', event => {
    const root = activeDialog;
    if (!root) return;
    if (event.key === 'Escape') {
      event.preventDefault();
      if (activeDialog) {
        const close = activeDialog.querySelector('button[onclick^="close"]');
        close?.click();
      }
    }
    if (event.key === 'Tab') {
      const items = focusable(root);
      const first = items[0], last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
  });
  document.querySelectorAll('a[id^="export-"]').forEach(link => link.addEventListener('click', async event => {
    event.preventDefault();
    const label = link.textContent;
    link.textContent = 'Menyiapkan unduhan...';
    try {
      const response = await fetch(link.href, { headers: { Authorization: 'Bearer ' + (localStorage.getItem('wvc_admin_token') || '') } });
      if (!response.ok) throw new Error('Unduhan gagal. Coba lagi atau masuk kembali.');
      const url = URL.createObjectURL(await response.blob());
      const download = document.createElement('a');
      download.href = url;
      download.download = link.id === 'export-results' ? 'hasil-voting.xlsx' : 'transaksi.xlsx';
      download.click();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (error) {
      let feedback = document.getElementById('export-feedback');
      if (!feedback) {
        feedback = document.createElement('p');
        feedback.id = 'export-feedback';
        feedback.className = 'notice notice-error';
        feedback.setAttribute('role', 'alert');
        link.parentElement.after(feedback);
      }
      feedback.textContent = error.message;
    } finally { link.textContent = label; }
  }));
});
