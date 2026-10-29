(() => {
  'use strict';

  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));
  const currentPage = document.body.dataset.page || 'home';

  async function api(url, options = {}) {
    const config = { method: options.method || 'GET', credentials: 'same-origin', headers: { ...(options.headers || {}) } };
    if (options.body !== undefined) {
      config.headers['Content-Type'] = 'application/json';
      config.body = JSON.stringify(options.body);
    }
    const response = await fetch(url, config);
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.error || `Request failed (${response.status}).`);
    return result;
  }

  function escapeHtml(value) {
    return String(value ?? '').replace(/[&<>"']/g, (character) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[character]));
  }

  function getInitials(name) {
    return String(name || 'Student').trim().split(/\s+/).slice(0, 2).map((part) => part[0] || '').join('').toUpperCase() || 'ST';
  }

  function showFlash(message, type = 'info') {
    const region = $('.flash-region');
    if (!region) return;
    region.innerHTML = `<div class="flash flash-${type}" role="status"><span>${escapeHtml(message)}</span><button class="flash-dismiss" type="button" aria-label="Dismiss message">×</button></div>`;
    const button = $('.flash-dismiss', region);
    if (button) button.addEventListener('click', () => { region.innerHTML = ''; });
    region.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }

  function showFormMessage(form, message, type = 'error') {
    const owner = form.closest('.auth-form-wrap, .form-panel') || form.parentElement;
    let box = $('[data-form-message]', owner);
    if (!box) {
      box = document.createElement('div');
      box.className = 'form-message';
      box.setAttribute('data-form-message', '');
      owner.insertBefore(box, form);
    }
    box.className = `form-message form-message-${type}`;
    box.textContent = message;
    box.hidden = false;
  }

  function tagsMarkup(items, className = '') {
    if (!items || !items.length) return '<span class="muted-copy">Not added yet</span>';
    return items.map((item) => `<span class="tag ${className}">${escapeHtml(item)}</span>`).join('');
  }

  function studentCard(student, featured = false) {
    const details = [student.course, student.year].filter(Boolean).join(' · ') || 'CampusConnect student';
    const skillTags = (student.skills || []).slice(0, 4).map((skill) => `<span class="tag">${escapeHtml(skill)}</span>`).join('');
    const bio = student.bio ? escapeHtml(student.bio) : 'Building skills and looking for new learning opportunities.';
    return `<article class="student-card ${featured ? 'featured-student' : ''}">
      <div class="student-card-top"><div class="avatar avatar-${(Number(student.id) % 5) + 1}">${escapeHtml(student.initials || getInitials(student.name))}</div><div class="student-card-title"><h3>${escapeHtml(student.name)}</h3><p>${escapeHtml(details)}</p></div></div>
      <p class="student-college">${escapeHtml(student.college || 'College not added')}</p>
      <p class="student-bio">${bio}</p>
      <div class="tag-list">${skillTags || '<span class="tag tag-muted">No skills added</span>'}</div>
      <a class="text-link student-card-link" href="/student.html?id=${encodeURIComponent(student.id)}">View profile <span aria-hidden="true">→</span></a>
    </article>`;
  }

  function renderStudents(container, students, emptyTitle = 'No students found', emptyText = 'Try a different search or check back later.') {
    if (!container) return;
    if (!students || !students.length) {
      container.innerHTML = `<div class="empty-state"><div class="empty-state-icon">⌕</div><h3>${escapeHtml(emptyTitle)}</h3><p>${escapeHtml(emptyText)}</p></div>`;
      return;
    }
    container.innerHTML = students.map((student) => studentCard(student)).join('');
  }

  function setupNavigation(user) {
    const toggle = $('.menu-toggle');
    const links = $('.nav-links');
    if (!links) return;

    if (user) {
      links.innerHTML = `
        <a href="/" data-nav="home">Home</a>
        <a href="/dashboard.html" data-nav="dashboard">Dashboard</a>
        <a href="/discover.html" data-nav="discover">Discover</a>
        <a href="/requests.html" data-nav="requests">Requests</a>
        <a href="/chat.html" data-nav="chat">Chats</a>
        <a href="/profile.html" data-nav="profile">Profile</a>
        <button type="button" class="nav-logout-button" id="logout-button">Log out</button>`;
      const logout = $('#logout-button', links);
      logout?.addEventListener('click', async () => {
        try {
          await api('/api/auth/logout', { method: 'POST', body: {} });
          window.location.href = '/';
        } catch (error) { showFlash(error.message, 'error'); }
      });
    } else {
      links.innerHTML = `
        <a href="/" data-nav="home">Home</a>
        <a href="/#features">About</a>
        <a href="/login.html" data-nav="login">Login</a>
        <a href="/register.html" class="nav-register" data-nav="register">Register</a>`;
    }

    const activeLink = $(`[data-nav="${currentPage}"]`, links);
    activeLink?.classList.add('active');

    if (toggle) {
      toggle.addEventListener('click', () => {
        const opened = toggle.getAttribute('aria-expanded') === 'true';
        toggle.setAttribute('aria-expanded', String(!opened));
        toggle.setAttribute('aria-label', opened ? 'Open navigation menu' : 'Close navigation menu');
        links.classList.toggle('is-open', !opened);
      });
      links.addEventListener('click', (event) => {
        if (event.target.closest('a, button')) {
          links.classList.remove('is-open');
          toggle.setAttribute('aria-expanded', 'false');
          toggle.setAttribute('aria-label', 'Open navigation menu');
        }
      });
      window.addEventListener('resize', () => {
        if (window.innerWidth > 780) {
          links.classList.remove('is-open');
          toggle.setAttribute('aria-expanded', 'false');
          toggle.setAttribute('aria-label', 'Open navigation menu');
        }
      });
    }
  }

  function prepareHome(user) {
    const primary = $('[data-home-primary]');
    const secondary = $('[data-home-secondary]');
    if (user) {
      if (primary) { primary.href = '/discover.html'; primary.innerHTML = 'Discover students <span aria-hidden="true">→</span>'; }
      if (secondary) { secondary.href = '/discover.html'; secondary.innerHTML = 'Find students <span aria-hidden="true">→</span>'; }
    }
    api('/api/public/students?limit=3').then((result) => {
      if (!result.data || !result.data.length) return;
      const strip = $('#featured-strip');
      const cards = $('#featured-students');
      if (strip && cards) {
        cards.innerHTML = result.data.map((student) => studentCard(student, true)).join('');
        strip.hidden = false;
      }
    }).catch(() => { /* The homepage remains useful when the database has not been configured yet. */ });
  }

  async function prepareLogin() {
    const form = $('[data-form="login"]');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const submit = $('button[type="submit"]', form);
      submit.disabled = true;
      try {
        const formData = new FormData(form);
        await api('/api/auth/login', { method: 'POST', body: { email: formData.get('email'), password: formData.get('password') } });
        window.location.href = '/dashboard.html';
      } catch (error) {
        showFormMessage(form, error.message);
      } finally { submit.disabled = false; }
    });
  }

  async function prepareRegister() {
    const form = $('[data-form="register"]');
    if (!form) return;
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const submit = $('button[type="submit"]', form);
      submit.disabled = true;
      const formData = new FormData(form);
      const splitTags = (value) => String(value || '').split(',').map((item) => item.trim()).filter(Boolean);
      try {
        await api('/api/auth/register', { method: 'POST', body: {
          name: formData.get('name'), email: formData.get('email'), password: formData.get('password'),
          college: formData.get('college'), course: formData.get('course'), year: formData.get('year'),
          skills: splitTags(formData.get('skills')), interests: splitTags(formData.get('interests'))
        }});
        window.location.href = '/dashboard.html';
      } catch (error) {
        showFormMessage(form, error.message);
      } finally { submit.disabled = false; }
    });
  }

  async function prepareDashboard() {
    try {
      const data = await api('/api/dashboard');
      const firstName = String(data.user.name || 'student').split(/\s+/)[0];
      const firstNameNode = $('#dashboard-first-name');
      if (firstNameNode) firstNameNode.textContent = firstName;
      $('#stat-students').textContent = data.student_count;
      $('#stat-received').textContent = data.pending_received;
      $('#stat-sent').textContent = data.pending_sent;
      const nudge = $('#profile-nudge');
      if (nudge && (!data.user.skills?.length || !data.user.college || !data.user.bio)) nudge.hidden = false;
      renderStudents($('#recommended-students'), data.recommended, 'Your community starts here', 'When other students join CampusConnect, their profiles will appear here.');
    } catch (error) {
      showFlash(error.message, 'error');
      renderStudents($('#recommended-students'), [], 'Students could not be loaded', 'Check the backend and database connection, then refresh this page.');
    }
  }

  async function prepareDiscover() {
    const form = $('#discover-search-form');
    const input = $('#student-search');
    const clear = $('#clear-search');
    const title = $('#results-heading-title');
    const count = $('#student-count');
    const container = $('#student-results');
    async function search(query = '') {
      if (count) count.textContent = 'Searching…';
      try {
        const data = await api(`/api/students?q=${encodeURIComponent(query)}`);
        renderStudents(container, data.data, query ? 'No matching students yet' : 'No student profiles yet', query ? 'Try another skill or search term.' : 'Invite a classmate to create a profile and appear in Discover.');
        if (title) title.textContent = query ? 'Search results' : 'Explore the community';
        if (count) count.textContent = `${data.count} student${data.count === 1 ? '' : 's'}`;
        if (clear) clear.hidden = !query;
      } catch (error) {
        showFlash(error.message, 'error');
        if (count) count.textContent = 'Unavailable';
        renderStudents(container, [], 'Could not load students', 'Check the backend and MySQL connection, then refresh.');
      }
    }
    form?.addEventListener('submit', (event) => { event.preventDefault(); search(input.value.trim()); });
    clear?.addEventListener('click', () => { input.value = ''; search(''); });
    await search(new URLSearchParams(window.location.search).get('q') || '');
    if (input && new URLSearchParams(window.location.search).get('q')) input.value = new URLSearchParams(window.location.search).get('q');
  }

  function updateProfileSummary(user) {
    const name = user.name || 'Your name';
    const initials = user.initials || getInitials(name);
    ['profile-avatar-large', 'profile-summary-avatar'].forEach((id) => { const node = document.getElementById(id); if (node) node.textContent = initials; });
    const setText = (id, value) => { const node = document.getElementById(id); if (node) node.textContent = value; };
    setText('profile-summary-name', name);
    setText('profile-summary-course', [user.course, user.year].filter(Boolean).join(' · ') || 'Student');
    setText('profile-summary-college', user.college || 'Add your college');
    setText('profile-skill-count', (user.skills || []).length);
    setText('profile-interest-count', (user.interests || []).length);
  }

  async function prepareProfile() {
    const form = $('#profile-form');
    try {
      const result = await api('/api/auth/me');
      if (!result.user) { window.location.href = '/login.html'; return; }
      const user = result.user;
      ['name', 'email', 'college', 'course', 'bio'].forEach((name) => { const field = $(`[name="${name}"]`, form); if (field) field.value = user[name] || ''; });
      const yearField = $('[name="year"]', form); if (yearField) yearField.value = user.year || '';
      const skillsField = $('[name="skills"]', form); if (skillsField) skillsField.value = (user.skills || []).join(', ');
      const interestsField = $('[name="interests"]', form); if (interestsField) interestsField.value = (user.interests || []).join(', ');
      updateProfileSummary(user);
    } catch (error) { showFlash(error.message, 'error'); }

    form?.addEventListener('submit', async (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const splitTags = (value) => String(value || '').split(',').map((item) => item.trim()).filter(Boolean);
      const submit = $('button[type="submit"]', form);
      submit.disabled = true;
      try {
        const result = await api('/api/profile', { method: 'PUT', body: {
          name: formData.get('name'), college: formData.get('college'), course: formData.get('course'), year: formData.get('year'),
          bio: formData.get('bio'), skills: splitTags(formData.get('skills')), interests: splitTags(formData.get('interests'))
        }});
        updateProfileSummary(result.user);
        showFormMessage(form, result.message, 'success');
      } catch (error) { showFormMessage(form, error.message, 'error'); }
      finally { submit.disabled = false; }
    });
  }

  async function prepareStudentProfile() {
    const root = $('#student-profile-root');
    const studentId = new URLSearchParams(window.location.search).get('id');
    if (!studentId || !/^\d+$/.test(studentId)) {
      root.innerHTML = '<div class="empty-state"><h3>Student not found</h3><p>Choose a student from Discover to view their profile.</p><a class="button button-secondary" href="/discover.html">Discover students</a></div>';
      return;
    }
    try {
      const result = await api(`/api/students/${encodeURIComponent(studentId)}`);
      const student = result.student;
      const relation = result.relationship;
      let action = '';
      if (relation.connected) action = `<span class="status-badge status-accepted">✓ Connected</span><a class="button button-primary" href="/chat.html?request_id=${Number(relation.accepted_request_id)}">Message <span aria-hidden="true">→</span></a>`;
      else if (relation.outgoing_status === 'pending') action = '<span class="status-badge status-pending">Request pending</span>';
      else if (relation.incoming_status === 'pending') action = '<span class="status-badge status-pending">This student has requested to connect. Review your requests.</span><a class="button button-secondary" href="/requests.html">View requests</a>';
      else action = `<form class="request-form" id="send-request-form"><div class="form-field"><label for="request-message">Message <span class="field-optional">(optional)</span></label><textarea id="request-message" name="message" rows="2" maxlength="500" placeholder="Hi! I'd like to collaborate with you."></textarea></div><button type="submit" class="button button-primary">${relation.outgoing_status === 'rejected' ? 'Send request again' : 'Connect with student'} <span aria-hidden="true">→</span></button></form>`;
      root.innerHTML = `<section class="public-profile-card">
        <div class="public-profile-top"><div class="profile-avatar-large avatar-${(Number(student.id) % 5) + 1}">${escapeHtml(student.initials || getInitials(student.name))}</div><div class="public-profile-main"><span class="eyebrow">STUDENT PROFILE</span><h1>${escapeHtml(student.name)}</h1><p class="public-profile-meta">${escapeHtml([student.course, student.year, student.college].filter(Boolean).join(' · ') || 'CampusConnect student')}</p></div><div class="profile-action-area">${action}</div></div>
        <div class="public-profile-body"><section class="profile-detail-section"><h2>About</h2><p>${escapeHtml(student.bio || 'This student has not added an introduction yet.')}</p></section><section class="profile-detail-section"><h2>Skills</h2><div class="tag-list tag-list-large">${tagsMarkup(student.skills)}</div></section><section class="profile-detail-section"><h2>Interests</h2><div class="tag-list tag-list-large">${tagsMarkup(student.interests, 'tag-interest')}</div></section></div>
      </section>`;
      const form = $('#send-request-form', root);
      form?.addEventListener('submit', async (event) => {
        event.preventDefault();
        const submit = $('button[type="submit"]', form); submit.disabled = true;
        try {
          await api('/api/requests', { method: 'POST', body: { receiver_id: student.id, message: $('[name="message"]', form).value } });
          showFlash('Collaboration request sent.', 'success');
          await prepareStudentProfile();
        } catch (error) { showFlash(error.message, 'error'); submit.disabled = false; }
      });
    } catch (error) {
      root.innerHTML = `<div class="empty-state"><h3>Could not load this profile</h3><p>${escapeHtml(error.message)}</p><a class="button button-secondary" href="/discover.html">Back to Discover</a></div>`;
    }
  }

  function requestCard(item, received) {
    const student = item.student || {};
    const details = [student.course, student.year, student.college].filter(Boolean).join(' · ') || 'CampusConnect student';
    const dateText = item.created_at ? new Date(item.created_at).toLocaleDateString() : '';
    const status = escapeHtml(item.status || 'pending');
    let controls = `<span class="status-badge status-${status}">${status}</span>`;
    if (received && item.status === 'pending') {
      controls = `<div class="request-controls"><button type="button" class="button button-primary button-small" data-request-action="accepted" data-request-id="${Number(item.id)}">Accept</button><button type="button" class="button button-quiet button-small" data-request-action="rejected" data-request-id="${Number(item.id)}">Reject</button></div>`;
    } else if (item.status === 'accepted') {
      controls = `<div class="request-controls"><span class="status-badge status-accepted">Accepted</span><a class="button button-secondary button-small" href="/chat.html?request_id=${Number(item.id)}">Message <span aria-hidden="true">→</span></a></div>`;
    }
    return `<article class="request-card"><div class="avatar avatar-${(Number(student.id) % 5) + 1}">${escapeHtml(student.initials || getInitials(student.name))}</div><div class="request-person"><h3><a href="/student.html?id=${encodeURIComponent(student.id || '')}">${escapeHtml(student.name || 'Student')}</a></h3><p>${escapeHtml(details)}</p>${item.message ? `<blockquote>“${escapeHtml(item.message)}”</blockquote>` : ''}<span class="request-date">${received ? 'Received' : 'Sent'} ${escapeHtml(dateText)}</span></div>${controls}</article>`;
  }

  async function prepareRequests() {
    const receivedNode = $('#received-requests');
    const sentNode = $('#sent-requests');
    try {
      const [received, sent] = await Promise.all([api('/api/requests?type=received'), api('/api/requests?type=sent')]);
      const pendingCount = (received.data || []).filter((item) => item.status === 'pending').length;
      const countNode = $('#received-pending-count'); if (countNode) countNode.textContent = `${pendingCount} pending`;
      if (receivedNode) receivedNode.innerHTML = received.data.length ? received.data.map((item) => requestCard(item, true)).join('') : '<div class="empty-state empty-state-compact"><div class="empty-state-icon">↙</div><h3>No requests received yet</h3><p>When a student asks to collaborate with you, the request will appear here.</p></div>';
      if (sentNode) sentNode.innerHTML = sent.data.length ? sent.data.map((item) => requestCard(item, false)).join('') : '<div class="empty-state empty-state-compact"><div class="empty-state-icon">↗</div><h3>You have not sent any requests</h3><p>Find a student whose skills match your interests and introduce yourself.</p><a class="button button-secondary" href="/discover.html">Discover students</a></div>';
    } catch (error) {
      showFlash(error.message, 'error');
      if (receivedNode) receivedNode.innerHTML = '<div class="empty-state"><p>Could not load requests.</p></div>';
      if (sentNode) sentNode.innerHTML = '<div class="empty-state"><p>Could not load requests.</p></div>';
    }

    [receivedNode, sentNode].filter(Boolean).forEach((node) => {
      $$('[data-request-action]', node).forEach((button) => {
        button.addEventListener('click', async () => {
          button.disabled = true;
          try {
            const id = button.dataset.requestId;
            const status = button.dataset.requestAction;
            const result = await api(`/api/requests/${encodeURIComponent(id)}`, { method: 'PATCH', body: { status } });
            showFlash(result.message, 'success');
            await prepareRequests();
          } catch (error) { showFlash(error.message, 'error'); button.disabled = false; }
        });
      });
    });
  }

  function chatTime(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  function chatConversationCard(item, selectedId) {
    const student = item.student || {};
    const id = Number(item.request_id);
    const isActive = id === Number(selectedId);
    const details = [student.course, student.year].filter(Boolean).join(' · ') || student.college || 'CampusConnect student';
    const preview = item.last_message || 'No messages yet. Say hello!';
    const time = item.last_message_at ? chatTime(item.last_message_at) : '';
    return `<a class="chat-conversation ${isActive ? 'is-active' : ''}" href="/chat.html?request_id=${id}" ${isActive ? 'aria-current="page"' : ''}>
      <span class="avatar avatar-${(Number(student.id) % 5) + 1}">${escapeHtml(student.initials || getInitials(student.name))}</span>
      <span class="chat-conversation-copy"><span class="chat-conversation-topline"><strong>${escapeHtml(student.name || 'Student')}</strong><time>${escapeHtml(time)}</time></span><span class="chat-conversation-meta">${escapeHtml(details)}</span><span class="chat-conversation-preview">${escapeHtml(preview)}</span></span>
    </a>`;
  }

  function renderChatMessages(container, messages, forceScroll = false) {
    if (!container) return;
    const wasNearBottom = forceScroll || container.scrollHeight - container.scrollTop - container.clientHeight < 80;
    if (!messages.length) {
      container.innerHTML = '<div class="chat-no-messages"><span aria-hidden="true">✦</span><strong>No messages yet</strong><p>Say hello and start planning your collaboration.</p></div>';
    } else {
      container.innerHTML = messages.map((item) => {
        const own = Boolean(item.is_mine);
        return `<article class="chat-message ${own ? 'chat-message-mine' : 'chat-message-theirs'}">
          <div class="chat-message-bubble"><p>${escapeHtml(item.message)}</p><time>${own ? 'You' : escapeHtml(item.sender_name || 'Student')} · ${escapeHtml(chatTime(item.created_at))}</time></div>
        </article>`;
      }).join('');
    }
    if (wasNearBottom) container.scrollTop = container.scrollHeight;
  }

  async function prepareChat() {
    const list = $('#chat-conversations');
    const panel = $('#chat-panel');
    const count = $('#chat-conversation-count');
    if (!list || !panel) return;

    let conversations;
    try {
      const result = await api('/api/chat/conversations');
      conversations = result.data || [];
    } catch (error) {
      list.innerHTML = `<div class="empty-state empty-state-compact"><h3>Chats could not load</h3><p>${escapeHtml(error.message)}</p></div>`;
      if (count) count.textContent = 'Unavailable';
      return;
    }

    if (count) count.textContent = String(conversations.length);
    if (!conversations.length) {
      list.innerHTML = '<div class="empty-state empty-state-compact"><div class="empty-state-icon">✉</div><h3>No chats yet</h3><p>When a collaboration request is accepted, you can message that student here.</p><a class="button button-secondary button-small" href="/discover.html">Discover students</a></div>';
      panel.innerHTML = '<div class="chat-panel-placeholder"><div class="chat-placeholder-icon" aria-hidden="true">✉</div><h2>No accepted connections yet</h2><p>Accept or receive an accepted collaboration request before starting a chat.</p><a class="button button-primary" href="/requests.html">View requests</a></div>';
      return;
    }

    const urlRequestId = new URLSearchParams(window.location.search).get('request_id');
    let selected = conversations.find((item) => String(item.request_id) === String(urlRequestId));
    if (!selected) selected = conversations[0];
    list.innerHTML = conversations.map((item) => chatConversationCard(item, selected.request_id)).join('');

    const student = selected.student || {};
    const studentId = Number(student.id);
    const requestId = Number(selected.request_id);
    panel.innerHTML = `<header class="chat-thread-header">
        <span class="avatar avatar-${(studentId % 5) + 1}">${escapeHtml(student.initials || getInitials(student.name))}</span>
        <div class="chat-thread-person"><h2>${escapeHtml(student.name || 'Student')}</h2><p>${escapeHtml([student.course, student.year, student.college].filter(Boolean).join(' · ') || 'CampusConnect student')}</p></div>
        <a class="text-link chat-profile-link" href="/student.html?id=${studentId}">View profile <span aria-hidden="true">→</span></a>
      </header>
      <div class="chat-messages" id="chat-messages" role="log" aria-live="polite" aria-label="Messages"><div class="chat-loading">Loading messages…</div></div>
      <form class="chat-composer" id="chat-form">
        <label class="sr-only" for="chat-message-input">Your message</label>
        <textarea id="chat-message-input" name="message" rows="2" maxlength="2000" placeholder="Write a message…" required></textarea>
        <button type="submit" class="button button-primary" id="chat-send-button">Send <span aria-hidden="true">↑</span></button>
        <p class="chat-composer-note">Please be respectful. Maximum 2,000 characters per message.</p>
      </form>`;

    const messageList = $('#chat-messages', panel);
    let lastMessageId = 0;
    async function refreshMessages(forceScroll = false) {
      const result = await api(`/api/chat/conversations/${requestId}/messages`);
      const messages = result.data || [];
      const newestId = messages.length ? Number(messages[messages.length - 1].id) : 0;
      if (newestId !== lastMessageId || forceScroll) {
        renderChatMessages(messageList, messages, forceScroll || lastMessageId === 0);
        lastMessageId = newestId;
      }
    }

    const form = $('#chat-form', panel);
    const input = $('#chat-message-input', form);
    const send = $('#chat-send-button', form);
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message) { input.focus(); return; }
      send.disabled = true;
      try {
        await api(`/api/chat/conversations/${requestId}/messages`, { method: 'POST', body: { message } });
        input.value = '';
        await refreshMessages(true);
      } catch (error) {
        showFlash(error.message, 'error');
      } finally {
        send.disabled = false;
        input.focus();
      }
    });

    try {
      await refreshMessages(true);
    } catch (error) {
      messageList.innerHTML = `<div class="empty-state empty-state-compact"><p>${escapeHtml(error.message)}</p></div>`;
    }
    window.setInterval(async () => {
      if (document.hidden) return;
      try { await refreshMessages(false); } catch (_error) { /* Keep the open thread visible if a temporary poll fails. */ }
    }, 4000);
  }

  async function initialize() {
    let auth = { authenticated: false, user: null };
    try { auth = await api('/api/auth/me'); }
    catch (error) { if (currentPage !== 'home') showFlash(error.message, 'error'); }

    setupNavigation(auth.user || null);
    if (document.body.hasAttribute('data-protected') && !auth.authenticated) {
      window.location.replace('/login.html');
      return;
    }
    if (auth.authenticated && (currentPage === 'login' || currentPage === 'register')) {
      window.location.replace('/dashboard.html');
      return;
    }

    switch (currentPage) {
      case 'home': prepareHome(auth.user); break;
      case 'login': prepareLogin(); break;
      case 'register': prepareRegister(); break;
      case 'dashboard': prepareDashboard(); break;
      case 'discover': prepareDiscover(); break;
      case 'profile': prepareProfile(); break;
      case 'student': prepareStudentProfile(); break;
      case 'requests': prepareRequests(); break;
      case 'chat': prepareChat(); break;
      default: break;
    }
  }

  document.addEventListener('DOMContentLoaded', initialize);
})();
