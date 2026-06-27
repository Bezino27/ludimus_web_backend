(function () {
  function getSectionType() {
    const field = document.querySelector('select[name="section_type"]');
    return field ? field.value : "";
  }

  function findSectionType(row) {
    return row.querySelector('select[name$="-section_type"], select[name="section_type"]');
  }

  function setVisible(elements, visible) {
    elements.forEach((element) => {
      element.style.display = visible ? "" : "none";
    });
  }

  function setFieldVisible(row, fieldName, visible) {
    setVisible(
      row.querySelectorAll(`.field-${fieldName}, [class*="field-${fieldName}"]`),
      visible,
    );
  }

  function updatePageInlineRow(row) {
    const sectionType = findSectionType(row);

    if (!sectionType) {
      return;
    }

    const value = sectionType.value;

    setFieldVisible(row, "content", value === "custom_text");
    setFieldVisible(row, "image", value === "hero");
  }

  function updatePageInlineRows() {
    document
      .querySelectorAll(".dynamic-sections, tr")
      .forEach((row) => updatePageInlineRow(row));
  }

  function updateSectionAdminForm() {
    const value = getSectionType();

    if (!value) {
      return;
    }

    setVisible(
      document.querySelectorAll(".form-row.field-content"),
      value === "custom_text",
    );
    setVisible(
      document.querySelectorAll(".form-row.field-image"),
      value === "hero",
    );

    const usesItems = value === "documents" || value === "custom_links";
    const itemGroups = document.querySelectorAll(".js-inline-admin-formset, .inline-group");

    itemGroups.forEach((group) => {
      if (group.id && group.id.includes("items")) {
        group.style.display = usesItems ? "" : "none";
      }
    });

    document
      .querySelectorAll(".dynamic-items, #items-group tr")
      .forEach((row) => {
        setFieldVisible(row, "file", value === "documents");
        setFieldVisible(row, "url", value === "custom_links");
      });
  }

  document.addEventListener("DOMContentLoaded", () => {
    updatePageInlineRows();
    updateSectionAdminForm();

    document.addEventListener("change", (event) => {
      const target = event.target;

      if (
        target instanceof HTMLSelectElement &&
        (target.name.endsWith("-section_type") || target.name === "section_type")
      ) {
        const row = target.closest(".dynamic-sections, tr");

        if (row) {
          updatePageInlineRow(row);
        }

        updateSectionAdminForm();
      }
    });

    document.body.addEventListener("formset:added", (event) => {
      if (event.target instanceof HTMLElement) {
        updatePageInlineRow(event.target);
        updateSectionAdminForm();
      }
    });
  });
})();
