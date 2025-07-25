// Custom JS for Cricket Club Manager 

// Document ready functionality
document.addEventListener('DOMContentLoaded', function () {
    // Auto-focus functionality for forms
    initializeAutoFocus();
    
    // Initialize form date defaults
    initializeDateDefaults();
    
    // Initialize create match functionality
    initializeCreateMatchFunctionality();
    
    // Initialize player card hover effects
    initializePlayerCardHovers();
    
    // Initialize member checkbox functionality
    initializeMemberCheckbox();
    
    // Initialize table filtering
    initializeTableFiltering();
});

// Auto-focus functionality
function initializeAutoFocus() {
    // Auto-focus name input on add player page
    const nameInput = document.getElementById('name');
    if (nameInput) {
        nameInput.focus();
    }
    
    // Auto-focus player select on add payment page
    const playerSelect = document.getElementById('player_id');
    if (playerSelect) {
        playerSelect.focus();
    }
}

// Date defaults
function initializeDateDefaults() {
    const today = new Date().toISOString().split('T')[0];
    
    // Set today's date as default for create match
    const matchDateInput = document.getElementById('date');
    if (matchDateInput && !matchDateInput.value) {
        matchDateInput.value = today;
    }
    
    // Set today's date as default for add payment if not already set
    const paymentDateInput = document.getElementById('date');
    if (paymentDateInput && !paymentDateInput.value) {
        paymentDateInput.value = today;
    }
}

// Create Match functionality
function initializeCreateMatchFunctionality() {
    // Initialize player filtering if on match creation page
    initializePlayerFiltering();
    
    const selectAllCheckbox = document.getElementById('select_all');
    const playerCheckboxes = document.querySelectorAll('.player-checkbox');
    
    if (selectAllCheckbox && playerCheckboxes.length > 0) {
        // Select all functionality (updated to work with filtering)
        selectAllCheckbox.addEventListener('change', function () {
            // Only affect visible players
            const visiblePlayerCheckboxes = document.querySelectorAll('.player-card-item:not([style*="display: none"]) .player-checkbox');
            visiblePlayerCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
            });
            updateSelectAllForVisible();
        });

        // Update select all when individual checkboxes change
        playerCheckboxes.forEach(checkbox => {
            checkbox.addEventListener('change', function () {
                updateSelectAllForVisible();
            });
        });
        
        // Initialize the select all state and selected counter
        updateSelectAllForVisible();
    }
}

// Player card hover effects for create match
function initializePlayerCardHovers() {
    document.querySelectorAll('.player-card').forEach(card => {
        card.addEventListener('mouseenter', function () {
            this.style.borderColor = '#007aff';
            this.style.background = 'rgba(0, 122, 255, 0.02)';
        });

        card.addEventListener('mouseleave', function () {
            this.style.borderColor = '#f0f0f0';
            this.style.background = 'transparent';
        });
    });
}

// Member checkbox functionality for edit player
function initializeMemberCheckbox() {
    const isMemberCheckbox = document.getElementById('is_member');
    const membershipDetails = document.getElementById('membershipDetails');
    
    if (isMemberCheckbox && membershipDetails) {
        isMemberCheckbox.addEventListener('change', function () {
            membershipDetails.style.display = this.checked ? 'block' : 'none';
        });
    }
}

// Player Details Modal functionality
function showPlayerDetails(playerId) {
    // Show loading state
    const modalContent = document.getElementById('playerDetailsContent');
    if (!modalContent) return;
    
    modalContent.innerHTML = `
        <div class="text-center py-4">
            <div class="spinner-border text-primary" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
        </div>
    `;

    fetch(`/api/player/${playerId}/balance`)
        .then(response => response.json())
        .then(data => {
            const content = `
                <div class="row g-4">
                    <div class="col-md-6">
                                                 <h6 class="section-header">
                             <i class="fas fa-user section-header-icon icon-primary"></i>
                             Player Information
                         </h6>
                         <div class="list-group list-group-flush">
                             <div class="list-group-item border-0 px-0 d-flex justify-content-between">
                                 <span class="text-secondary">Name:</span>
                                 <strong class="text-primary">${data.name}</strong>
                             </div>
                             <div class="list-group-item border-0 px-0 d-flex justify-content-between">
                                 <span class="text-secondary">Total Owed:</span>
                                 <strong class="text-primary">&pound;${data.total_owed.toFixed(2)}</strong>
                             </div>
                             <div class="list-group-item border-0 px-0 d-flex justify-content-between">
                                 <span class="text-secondary">Total Paid:</span>
                                 <strong class="balance-positive">&pound;${data.total_paid.toFixed(2)}</strong>
                             </div>
                             <div class="list-group-item border-0 px-0 d-flex justify-content-between">
                                 <span class="text-secondary">Balance:</span>
                                 <strong class="${data.balance > 0 ? 'balance-negative' : 'balance-positive'}">
                                     &pound;${Math.abs(data.balance).toFixed(2)} ${data.balance > 0 ? '(Owed)' : '(Credit)'}
                                 </strong>
                             </div>
                         </div>
                     </div>
                     <div class="col-md-6">
                         <h6 class="section-header">
                             <i class="fas fa-bolt section-header-icon icon-primary"></i>
                             Quick Actions
                         </h6>
                        <div class="d-grid gap-2">
                            <a href="/payments/add?player_id=${playerId}" class="btn btn-success">
                                <i class="fas fa-plus me-2"></i> Record Payment
                            </a>
                            <a href="/players/edit/${playerId}" class="btn btn-outline-primary">
                                <i class="fas fa-edit me-2"></i> Edit Player
                            </a>
                        </div>
                    </div>
                </div>
            `;
            modalContent.innerHTML = content;
            new bootstrap.Modal(document.getElementById('playerDetailsModal')).show();
        })
        .catch(error => {
            console.error('Error:', error);
            modalContent.innerHTML = `
                <div class="alert alert-custom alert-error-custom">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    Error loading player details. Please try again.
                </div>
            `;
        });
}

// Match Details Modal functionality
function showMatchDetails(matchId) {
    const modalContent = document.getElementById('matchDetailsContent');
    if (!modalContent) return;
    
    // For now, we'll show a simple message. In a real app, you'd fetch match details via API
    const content = `
        <div class="alert alert-custom alert-success-custom">
            <i class="fas fa-info-circle"></i> 
            Match details feature coming soon! This would show the list of players who attended this match.
        </div>
    `;
    modalContent.innerHTML = content;
    new bootstrap.Modal(document.getElementById('matchDetailsModal')).show();
}

// Payment Details Modal functionality
function showPaymentDetails(paymentId) {
    const modalContent = document.getElementById('paymentDetailsContent');
    if (!modalContent) return;
    
    // For now, we'll show a simple message. In a real app, you'd fetch payment details via API
    const content = `
        <div class="alert alert-custom alert-success-custom">
            <i class="fas fa-info-circle"></i> 
            Payment details feature coming soon! This would show more detailed information about the payment.
        </div>
    `;
    modalContent.innerHTML = content;
    new bootstrap.Modal(document.getElementById('paymentDetailsModal')).show();
}

// Utility functions
function confirmDelete(playerName) {
    return confirm(`Are you sure you want to delete ${playerName}?`);
}

// Table Filtering functionality
function initializeTableFiltering() {
    const filterInputs = document.querySelectorAll('.table-filter-input');
    const filterSelects = document.querySelectorAll('.table-filter-select');
    
    if (filterInputs.length === 0 && filterSelects.length === 0) {
        return;
    }
    
    // Add debounced search for better performance
    filterInputs.forEach((input) => {
        let timeoutId;
        input.addEventListener('input', function() {
            clearTimeout(timeoutId);
            const inputElement = this;
            timeoutId = setTimeout(() => {
                filterTable(inputElement);
            }, 250); // 250ms delay for smoother typing
        });
    });
    
    filterSelects.forEach((select) => {
        select.addEventListener('change', function() {
            filterTable(this);
        });
    });
}

function filterTable(filterElement) {
    const card = filterElement.closest('.card');
    const tableContainer = card.querySelector('.table-container');
    
    if (!tableContainer) {
        return;
    }
    
    const table = tableContainer.querySelector('table');
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // Get filter values
    const searchInput = card.querySelector('.table-filter-input');
    const statusSelect = card.querySelector('.table-filter-select');
    
    const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
    const statusFilter = statusSelect ? statusSelect.value.toLowerCase() : 'all';
    
    let visibleCount = 0;
    
    rows.forEach(row => {
        const cells = Array.from(row.querySelectorAll('td'));
        
        // Get text content for search (exclude action buttons)
        const searchableText = cells.slice(0, -1).map(cell => {
            // Get text content but exclude button text
            const clone = cell.cloneNode(true);
            const buttons = clone.querySelectorAll('button, a');
            buttons.forEach(btn => btn.remove());
            return clone.textContent.toLowerCase();
        }).join(' ');
        
        // Check search term
        const matchesSearch = searchTerm === '' || searchableText.includes(searchTerm);
        
        // Check status filter (assuming status is in second column - index 1)
        let matchesStatus = true;
        if (statusFilter !== 'all' && cells.length > 1) {
            const statusCell = cells[1];
            if (statusCell) {
                const statusText = statusCell.textContent.toLowerCase();
                if (statusFilter === 'member') {
                    matchesStatus = statusText.includes('member') && !statusText.includes('non-member');
                } else if (statusFilter === 'non-member') {
                    matchesStatus = statusText.includes('non-member');
                }
            }
        }
        
        const shouldShow = matchesSearch && matchesStatus;
        row.style.display = shouldShow ? '' : 'none';
        
        if (shouldShow) {
            visibleCount++;
        }
    });
    
    // Update visible count
    const counter = card.querySelector('.table-counter');
    if (counter) {
        const totalRows = rows.length;
        if (visibleCount === totalRows) {
            counter.textContent = `${totalRows} players`;
        } else {
            counter.textContent = `${visibleCount} of ${totalRows} players`;
        }
    }
    
    // Show/hide empty state
    const emptyState = card.querySelector('.table-empty-state');
    const tableContainer2 = card.querySelector('.table-container');
    
    if (emptyState && tableContainer2) {
        if (visibleCount === 0) {
            emptyState.style.display = 'block';
            tableContainer2.style.display = 'none';
        } else {
            emptyState.style.display = 'none';
            tableContainer2.style.display = 'block';
        }
    }
}

// Clear table filters
function clearTableFilters(card) {
    const searchInput = card.querySelector('.table-filter-input');
    const statusSelect = card.querySelector('.table-filter-select');
    
    if (searchInput) {
        searchInput.value = '';
    }
    if (statusSelect) {
        statusSelect.value = 'all';
    }
    
    // Show all rows
    const tableContainer = card.querySelector('.table-container');
    if (tableContainer) {
        const rows = tableContainer.querySelectorAll('tbody tr');
        rows.forEach(row => {
            row.style.display = '';
        });
        
        // Update counter
        const counter = card.querySelector('.table-counter');
        if (counter) {
            counter.textContent = `${rows.length} players`;
        }
        
        // Hide empty state and show table
        const emptyState = card.querySelector('.table-empty-state');
        if (emptyState) {
            emptyState.style.display = 'none';
        }
        tableContainer.style.display = 'block';
    }
}

// Player Filtering functionality (for match creation)
function initializePlayerFiltering() {
    const filterInput = document.querySelector('.player-filter-input');
    const filterSelect = document.querySelector('.player-filter-select');
    
    if (!filterInput && !filterSelect) {
        return;
    }
    
    // Add debounced search for better performance
    if (filterInput) {
        let timeoutId;
        filterInput.addEventListener('input', function() {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                filterPlayers();
            }, 250);
        });
    }
    
    if (filterSelect) {
        filterSelect.addEventListener('change', function() {
            filterPlayers();
        });
    }
}

function filterPlayers() {
    const filterInput = document.querySelector('.player-filter-input');
    const filterSelect = document.querySelector('.player-filter-select');
    const playerItems = document.querySelectorAll('.player-card-item');
    const counter = document.querySelector('.player-counter');
    const emptyState = document.querySelector('.player-empty-state');
    const gridContainer = document.querySelector('.player-grid-container');
    
    const searchTerm = filterInput ? filterInput.value.toLowerCase().trim() : '';
    const statusFilter = filterSelect ? filterSelect.value.toLowerCase() : 'all';
    
    let visibleCount = 0;
    
    playerItems.forEach(item => {
        const playerName = item.getAttribute('data-player-name') || '';
        const playerStatus = item.getAttribute('data-player-status') || '';
        
        const matchesSearch = searchTerm === '' || playerName.includes(searchTerm);
        
        let matchesStatus = true;
        if (statusFilter !== 'all') {
            if (statusFilter === 'member') {
                matchesStatus = playerStatus === 'member';
            } else if (statusFilter === 'non-member') {
                matchesStatus = playerStatus === 'non-member';
            }
        }
        
        const shouldShow = matchesSearch && matchesStatus;
        item.style.display = shouldShow ? '' : 'none';
        
        if (shouldShow) {
            visibleCount++;
        }
    });
    
    // Update counter to show selected players instead of visible
    updateSelectedPlayerCounter();
    
    // Show/hide empty state
    if (emptyState && gridContainer) {
        if (visibleCount === 0) {
            emptyState.style.display = 'block';
            gridContainer.style.display = 'none';
        } else {
            emptyState.style.display = 'none';
            gridContainer.style.display = 'block';
        }
    }
    
    // Update "Select All" functionality to only affect visible players
    updateSelectAllForVisible();
}

function clearPlayerFilters() {
    const filterInput = document.querySelector('.player-filter-input');
    const filterSelect = document.querySelector('.player-filter-select');
    
    if (filterInput) filterInput.value = '';
    if (filterSelect) filterSelect.value = 'all';
    
    // Show all players
    const playerItems = document.querySelectorAll('.player-card-item');
    playerItems.forEach(item => {
        item.style.display = '';
    });
    
    // Update counter to show selected players
    updateSelectedPlayerCounter();
    
    // Hide empty state
    const emptyState = document.querySelector('.player-empty-state');
    const gridContainer = document.querySelector('.player-grid-container');
    if (emptyState && gridContainer) {
        emptyState.style.display = 'none';
        gridContainer.style.display = 'block';
    }
    
    // Update select all
    updateSelectAllForVisible();
}

function updateSelectAllForVisible() {
    const selectAllCheckbox = document.getElementById('select_all');
    if (!selectAllCheckbox) return;
    
    const visiblePlayerCheckboxes = Array.from(document.querySelectorAll('.player-card-item:not([style*="display: none"]) .player-checkbox'));
    const checkedVisibleBoxes = visiblePlayerCheckboxes.filter(cb => cb.checked);
    
    if (visiblePlayerCheckboxes.length === 0) {
        selectAllCheckbox.indeterminate = false;
        selectAllCheckbox.checked = false;
    } else if (checkedVisibleBoxes.length === visiblePlayerCheckboxes.length) {
        selectAllCheckbox.indeterminate = false;
        selectAllCheckbox.checked = true;
    } else if (checkedVisibleBoxes.length > 0) {
        selectAllCheckbox.indeterminate = true;
        selectAllCheckbox.checked = false;
    } else {
        selectAllCheckbox.indeterminate = false;
        selectAllCheckbox.checked = false;
    }
    
    // Update the selected player counter
    updateSelectedPlayerCounter();
}

// New function to update counter with selected players
function updateSelectedPlayerCounter() {
    const counter = document.querySelector('.player-counter');
    if (!counter) return;
    
    const allPlayerCheckboxes = document.querySelectorAll('.player-checkbox');
    const selectedCheckboxes = Array.from(allPlayerCheckboxes).filter(cb => cb.checked);
    const totalPlayers = allPlayerCheckboxes.length;
    const selectedCount = selectedCheckboxes.length;
    
    if (selectedCount === 0) {
        counter.textContent = `${totalPlayers} players`;
        counter.className = 'player-counter text-secondary text-sm';
    } else if (selectedCount === 1) {
        counter.textContent = `1 player selected`;
        counter.className = 'player-counter text-primary text-sm fw-medium';
    } else {
        counter.textContent = `${selectedCount} players selected`;
        counter.className = 'player-counter text-primary text-sm fw-medium';
    }
}

// Test function to verify JavaScript is working
function testFiltering() {
    console.log('🧪 Testing filtering system...');
    
    const filterInputs = document.querySelectorAll('.table-filter-input');
    const filterSelects = document.querySelectorAll('.table-filter-select');
    const cards = document.querySelectorAll('.card');
    const tables = document.querySelectorAll('table');
    
    console.log('Found elements:');
    console.log('- Filter inputs:', filterInputs.length);
    console.log('- Filter selects:', filterSelects.length);  
    console.log('- Cards:', cards.length);
    console.log('- Tables:', tables.length);
    
    if (filterInputs.length > 0) {
        console.log('✅ Filter inputs found');
        filterInputs[0].value = 'test';
        filterTable(filterInputs[0]);
    } else {
        console.log('❌ No filter inputs found');
    }
}

// Export functions to global scope for onclick handlers
window.showPlayerDetails = showPlayerDetails;
window.showMatchDetails = showMatchDetails;
window.showPaymentDetails = showPaymentDetails;
window.confirmDelete = confirmDelete;
window.clearTableFilters = clearTableFilters;
window.clearPlayerFilters = clearPlayerFilters;
window.testFiltering = testFiltering; 