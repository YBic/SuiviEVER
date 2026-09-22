/**
 * ever.js — JavaScript partagé (master page)
 * Horloge, spinner, commentaires, mot de passe affectation
 */

/* ---- Interception globale session expirée (401) ----
 * Quand la session Django expire, les appels AJAX reçoivent un 401 JSON
 * au lieu d'un redirect 302. On redirige vers /login/ proprement.
 */
$(document).ajaxError(function (event, xhr) {
  if (xhr.status === 401) {
    window.location.href = '/login/';
  }
});

/* ---- Datepicker DD/MM/YYYY (Flatpickr) ---- */
if (document.getElementById('filter-date')) {
  flatpickr('#filter-date', {
    locale:      'fr',
    dateFormat:  'Y-m-d',    // valeur interne envoyée au serveur
    altInput:    true,
    altFormat:   'd/m/Y',    // affichage utilisateur
    allowInput:  false,      // calendrier uniquement → champ readonly → pas d'autofill navigateur
    onReady: function (selectedDates, dateStr, instance) {
      // IMPORTANT : ne PAS utiliser autocomplete="new-password" — ce mot-clé
      // est reconnu par Edge/Chrome et OUVRE le gestionnaire de mots de passe
      // ("Saved passwords") par-dessus le calendrier. On neutralise l'autofill :
      if (instance.altInput) {
        instance.altInput.setAttribute('autocomplete', 'off');
        instance.altInput.setAttribute('name', 'filter-date-display'); // nom non-credential
        instance.altInput.setAttribute('readonly', 'readonly');        // pas d'autofill clavier (calendrier only)
        instance.altInput.setAttribute('data-lpignore', 'true');       // LastPass
        instance.altInput.setAttribute('data-form-type', 'other');     // Dashlane/1Password
        instance.altInput.setAttribute('data-1p-ignore', 'true');      // 1Password
      }
    },
  });
}

/**
 * setFilterDate(isoDate)
 * Met à jour le datepicker de filtre via l'API Flatpickr (pas $.val) pour que
 * l'altInput DD/MM/YYYY reste synchronisé. Utilisé par FS.restore() dans chaque
 * page JS. false = ne déclenche pas l'event "change" (loadData est appelé ensuite
 * explicitement).
 */
function setFilterDate(isoDate) {
  if (!isoDate) return;
  const fp = document.getElementById('filter-date')?._flatpickr;
  if (fp) fp.setDate(isoDate, false);
  else $('#filter-date').val(isoDate);
}

/* ---- Horloge ---- */
function updateClock() {
  const now = new Date();
  const pad = n => String(n).padStart(2, '0');
  $('#clock').text(
    `${pad(now.getDate())}/${pad(now.getMonth()+1)}/${now.getFullYear()} `+
    `${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}`
  );
}
setInterval(updateClock, 1000);
updateClock();

/* ---- Spinner ---- */
function showSpinner() { $('#loading-overlay').removeClass('d-none').css('display','flex'); }
function hideSpinner() { $('#loading-overlay').addClass('d-none'); }

/* ---- Rafraîchir (bouton header) ---- */
$('#btn-refresh').on('click', function () {
  $('#btn-refresh-data').trigger('click');
});

/* ---- CSRF token pour les requêtes POST ---- */
function getCsrfToken() {
  return $('[name=csrfmiddlewaretoken]').val() ||
         document.cookie.split('; ')
           .find(r => r.startsWith('csrftoken='))
           ?.split('=')[1] || '';
}

function ajaxPost(url, data) {
  return $.ajax({
    url,
    method: 'POST',
    contentType: 'application/json',
    headers: { 'X-CSRFToken': getCsrfToken() },
    data: JSON.stringify(data),
  });
}

/* ---- Colorisation taux ---- */
function rateClass(pct) {
  if (pct === null || pct === undefined || pct === '') return '';
  const val = parseFloat(String(pct).replace('%',''));
  if (isNaN(val)) return '';
  if (val >= 90) return 'good';
  if (val >= 60) return 'mid';
  return 'bad';
}

/* ---- Formatage d'un taux en % ---- */
function fmtRate(val, total) {
  if (!total || total === 0) return '—';
  return Math.round((val / total) * 100) + '%';
}

/* ---- Formatage date ISO → DD/MM/YYYY ---- */
function fmtDate(iso) {
  if (!iso || iso.length < 10) return iso || '';
  return iso.substring(8, 10) + '/' + iso.substring(5, 7) + '/' + iso.substring(0, 4);
}

/* ---- Bouton "Aujourd'hui" ---- */
$(document).on('click', '#btn-today', function () {
  const fp = document.getElementById('filter-date')?._flatpickr;
  if (fp) {
    fp.setDate(new Date(), true);   // true = déclenche le change event
  } else {
    const iso = new Date().toISOString().split('T')[0];
    $('#filter-date').val(iso).trigger('change');
  }
});

/* ---- Fraîcheur des données ---- */
let _lastRefreshTime = null;

function markRefresh() {
  _lastRefreshTime = new Date();
  _updateFreshness();
  $('#freshness').removeClass('d-none');
}

function _updateFreshness() {
  if (!_lastRefreshTime) return;
  const diffSec = Math.round((new Date() - _lastRefreshTime) / 1000);
  let txt;
  if (diffSec < 60)        txt = 'Actualisé à l\'instant';
  else if (diffSec < 3600) txt = `Il y a ${Math.floor(diffSec / 60)} min`;
  else                     txt = `Il y a ${Math.floor(diffSec / 3600)}h`;
  $('#freshness').text(txt);
}
setInterval(_updateFreshness, 30000);

/* ---- Auto-refresh (toutes les 5 min) ---- */
let _autoRefreshTimer = null;
const AUTO_REFRESH_MS = 5 * 60 * 1000;

$('#btn-autorefresh').on('click', function () {
  const $btn = $(this);
  if (_autoRefreshTimer) {
    clearInterval(_autoRefreshTimer);
    _autoRefreshTimer = null;
    $btn.removeClass('active');
    $btn.attr('title', 'Actualisation automatique (5 min)');
  } else {
    _autoRefreshTimer = setInterval(function () {
      $('#btn-refresh-data').trigger('click');
    }, AUTO_REFRESH_MS);
    $btn.addClass('active');
    $btn.attr('title', 'Désactiver l\'actualisation automatique');
  }
});

/* ================================================================
   MODAL COMMENTAIRE
   ================================================================ */
const modalCommentaire = new bootstrap.Modal('#modal-commentaire');
let cmntMode = 'aeroport';   // 'aeroport' (vol) | 'zone' (site)

$(document).on('click', '.btn-comment', function () {
  const $btn = $(this);
  cmntMode = $btn.data('mode') === 'zone' ? 'zone' : 'aeroport';
  const rang  = parseInt($btn.data('rang')) || 1;   // rang de l'enquêteur sur cette ligne
  // On affiche uniquement le slot correspondant au rang de la ligne cliquée
  const vac = rang === 2 ? ($btn.data('vac2') || '') : ($btn.data('vac1') || '');
  const vol = rang === 2 ? ($btn.data('vol2') || '') : ($btn.data('vol1') || '');
  // Libellé du 2e champ selon le contexte
  $('#cmnt-vol-label').text(cmntMode === 'zone' ? 'Commentaire site' : 'Commentaire vol');
  $('#cmnt-id-vacation').val($btn.data('id'));
  $('#cmnt-rang').val(rang);
  $('#cmnt-vacation-num').text($btn.data('num') || '');
  $('#cmnt-vac-1').val(vac);
  $('#cmnt-vol-1').val(vol);
  modalCommentaire.show();
});

$('#btn-save-commentaire').on('click', function () {
  const idVacation = $('#cmnt-id-vacation').val();
  if (!idVacation) return;

  const rang     = parseInt($('#cmnt-rang').val()) || 1;
  const $btn     = $(`.btn-comment[data-id="${idVacation}"]`);
  const editedVac = $('#cmnt-vac-1').val() || null;
  const editedVol = $('#cmnt-vol-1').val() || null;
  // Préserver le slot qui n'est pas édité (l'autre rang)
  const vac1 = rang === 1 ? editedVac : ($btn.data('vac1') || null);
  const vol1 = rang === 1 ? editedVol : ($btn.data('vol1') || null);
  const vac2 = rang === 2 ? editedVac : ($btn.data('vac2') || null);
  const vol2 = rang === 2 ? editedVol : ($btn.data('vol2') || null);

  const isZone = cmntMode === 'zone';
  const url     = isZone ? '/api/commentaire/zone/' : '/api/commentaire/';
  const payload = isZone
    ? {
        id_vacation_zone_site:      parseInt(idVacation),
        commentaire_vac_zone_1:     vac1,   // niveau vacation zone
        commentaire_vac_zonesite_1: vol1,   // niveau site
        commentaire_vac_zone_2:     vac2,
        commentaire_vac_zonesite_2: vol2,
      }
    : {
        id_vacation:       parseInt(idVacation),
        commentaire_vac_1: vac1,
        commentaire_vol_1: vol1,
        commentaire_vac_2: vac2,
        commentaire_vol_2: vol2,
      };

  showSpinner();
  ajaxPost(url, payload)
  .done(function (resp) {
    if (resp.status === 'ok') {
      modalCommentaire.hide();
      // Recharger : garantit des boutons à jour pour les 2 enquêteurs.
      if (isZone && typeof window.everReloadDetail === 'function') {
        window.everReloadDetail();
      } else if (typeof window.everReloadData === 'function') {
        window.everReloadData();
      }
    } else {
      alert('Erreur : ' + (resp.message || 'enregistrement du commentaire impossible.'));
    }
  })
  .fail(function () {
    alert('Erreur lors de l\'enregistrement du commentaire.');
  })
  .always(hideSpinner);
});

/* ================================================================
   MODAL MOT DE PASSE AFFECTATION
   ================================================================ */
const modalPassword = new bootstrap.Modal('#modal-password');

function checkAffectationPassword(onSuccess) {
  $('#password-error').addClass('d-none');
  $('#affectation-password').val('');
  modalPassword.show();

  $('#btn-check-password').off('click').on('click', function () {
    const pwd = $('#affectation-password').val();
    showSpinner();
    ajaxPost('/api/affectation/password/', { password: pwd })
    .done(function (resp) {
      if (resp.status === 'ok') {
        modalPassword.hide();
        if (typeof onSuccess === 'function') onSuccess();
      }
    })
    .fail(function () {
      $('#password-error').removeClass('d-none');
    })
    .always(hideSpinner);
  });
}
