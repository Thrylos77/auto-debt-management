document.addEventListener('DOMContentLoaded', function() {
    const customerTypeSelect = document.querySelector('#id_customer_type');
    const physicalInline = document.querySelector('.physical-inline');
    const moralInline = document.querySelector('.moral-inline');

    function toggleInlines() {
        if (!customerTypeSelect || !physicalInline || !moralInline) {
            return;
        }

        const selectedType = customerTypeSelect.value;

        if (selectedType === 'physical') {
            physicalInline.classList.remove('collapse');
            moralInline.classList.add('collapse');
        } else if (selectedType === 'moral') {
            moralInline.classList.remove('collapse');
            physicalInline.classList.add('collapse');
        }
    }

    // Toggle on page load
    toggleInlines();

    // Toggle on select change
    customerTypeSelect.addEventListener('change', toggleInlines);
});