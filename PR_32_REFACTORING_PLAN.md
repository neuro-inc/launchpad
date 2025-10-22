# PR #32 Refactoring Plan - Admin UI

This document tracks the refactoring work needed to address review comments from @dnddone on PR #32.

## Review Summary
The review identified that many custom implementations in the admin UI already exist in the codebase and should be reused to maintain consistency and reduce code duplication.

---

## Progress Tracker

### ✅ COMPLETED

1. **Replace manual toast management with existing toast.feature.tsx workflow**
   - ✅ Replaced `addToast()` and `dismissToast()` with `toast.success()`, `toast.error()`
   - ✅ Removed `toasts` state and Toast type import from AdminPage.tsx
   - File: `src/app/admin/AdminPage.tsx`

2. **Replace clientRequest with unified request() helper**
   - ✅ Changed all `clientRequest()` calls to `request()`
   - ✅ Updated import from `@utils/helpers`
   - File: `src/app/admin/AdminPage.tsx`

3. **Remove manual ToastContainer from AdminPage**
   - ✅ Removed `<ToastContainer toasts={toasts} onDismiss={dismissToast} />` from JSX
   - ✅ Removed ToastContainer import
   - File: `src/app/admin/AdminPage.tsx`

4. **Replace raw button elements with Button component**
   - ✅ Replaced raw `<button>` for "Refresh Data" with `<Button>` component
   - File: `src/app/admin/AdminPage.tsx` (line 211-217)

5. **Simplify delete handlers**
   - ✅ Refactored delete handlers to be async and directly handle confirmation
   - ✅ Removed separate confirmation state management
   - File: `src/app/admin/AdminPage.tsx`

6. **Remove redundant session/auth checks from admin/page.tsx**
   - ✅ Removed `getServerSession()`, `getAuthOptions()`, and `isAdmin()` checks
   - ✅ Middleware handles authentication (see `src/middleware.ts` lines 57-70)
   - File: `src/app/admin/page.tsx`

7. **Keep isAdmin helper for UI conditional rendering**
   - ✅ Decided to keep `src/utils/helpers/isAdmin.ts` for UI components
   - ✅ Middleware handles route-level access, UI uses helper for conditional display
   - Files: Used in `LayoutHeader.tsx` and `LayoutHeaderClient.tsx`

8. **Remove unnecessary API route files**
   - ✅ Deleted `src/app/api/admin/apps/import/route.ts`
   - ✅ Deleted `src/app/api/admin/templates/import/route.ts`
   - Reason: `request()` and `middleware.ts` handle authentication and proxying

9. **Remove custom Toast components**
   - ✅ Deleted `src/components/Admin/Toast.tsx`
   - ✅ Updated `src/components/Admin/index.ts` exports

10. **Remove SessionProvider**
    - ✅ Deleted `src/components/Providers/SessionProvider.tsx`
    - ✅ Deleted `src/components/Providers/index.ts`
    - Reason: Session is managed by middleware.ts

11. **Remove LayoutClient extensions**
    - ✅ Removed `LayoutClient.Container` and `LayoutClient.Wrapper` assignments
    - ✅ Cleaned up unused imports
    - File: `src/components/Ui/Layout/LayoutClient.tsx`

12. **Restore console.log in request.ts for debugging**
    - ✅ Added back console.log statements with eslint-disable comments
    - File: `src/utils/helpers/request.ts`

13. **Fix template instance foreign key relationship**
    - ✅ Fixed bug where `instance.templateName` references `template.name`, not `template.templateName`
    - ✅ Correctly disables `is_shared` and `is_internal` fields when template has instances
    - File: `src/components/Admin/ImportTemplateForm.tsx`

14. **Replace SVG icons with FontAwesome icons**
    - ✅ Replaced inline SVG with FontAwesome icons in CollapsibleSection (faChevronDown)
    - ✅ Replaced inline SVG with FontAwesome icons in FileUpload (faCloudArrowUp, faCircleCheck, faXmark)
    - Files: `src/components/Admin/CollapsibleSection.tsx`, `src/components/Admin/FileUpload.tsx`

15. **Replace raw buttons with Button component**
    - ✅ Replaced raw `<button>` with `<Button theme={false}>` in CollapsibleSection
    - File: `src/components/Admin/CollapsibleSection.tsx`

16. **Move Template and InstalledApp types to apps.ts**
    - ✅ Moved `Template`, `InstalledApp`, and `UnimportedInstance` types from admin.ts to apps.ts
    - ✅ Consolidated all app-related types in one location
    - Files: `src/types/apps.ts`, `src/types/admin.ts`

17. **Remove duplicate Toast types**
    - ✅ Removed `ToastType` and `Toast` types from admin.ts
    - Reason: Already defined in `toast.feature.tsx`
    - File: `src/types/admin.ts`

18. **Fix delete app instance endpoint**
    - ✅ Changed endpoint parameter from `id` to `appId` (app_id from API)
    - ✅ DELETE /api/v1/apps/instances/${appId} now uses correct identifier
    - ✅ Made InstalledApp.id required instead of optional for type safety
    - File: `src/app/admin/AdminPage.tsx`, `src/types/apps.ts`

19. **Simplify modal management using trigger pattern**
    - ✅ Deleted ImportTemplateModal and ImportAppModal wrapper components (156 lines removed)
    - ✅ Removed `isImportTemplateModalOpen` and `isImportAppModalOpen` state
    - ✅ Use Modal trigger pattern: `<Modal content={...}><Button>Trigger</Button></Modal>`
    - ✅ Form components used directly as modal content
    - Files: Deleted `ImportTemplateModal.tsx`, `ImportAppModal.tsx`; Modified `AdminPage.tsx`, `index.ts`

20. **Remove isOpen state from all modal management**
    - ✅ Delete confirmation modals: Changed from `{isOpen, template}` to `Template | null`
    - ✅ Delete confirmation modals: Changed from `{isOpen, instance}` to `InstalledApp | null`
    - ✅ Template view/edit modal: Changed from `{isOpen, template, mode}` to `{template, mode} | null`
    - ✅ Conditionally render modals based on data existence
    - ✅ Removed all `isOpen` boolean state (75 lines removed)
    - File: `src/app/admin/AdminPage.tsx`

---

## 🔄 IN PROGRESS

None currently

---

## 📋 TODO - High Priority

### Component Refactoring - Forms

10. **Refactor ImportAppForm to use react-hook-form**
    - Location: `src/components/Admin/ImportAppForm.tsx`
    - Replace: Manual form state with `useForm()` from react-hook-form
    - Remove: `useImmer` usage for form data
    - Priority: MEDIUM (nice to have but not blocking)

11. **Implement zod validation schemas**
    - Location: Create `src/components/Admin/schemas.ts` or similar
    - Add: Zod schemas for ImportAppRequest and ImportTemplateRequest
    - Replace: Manual validation logic (e.g., UUID regex check at line 74-80)
    - Priority: MEDIUM (nice to have but not blocking)

12. **Replace manual inputs/labels with Field.Input components**
    - Location: `src/components/Admin/ImportAppForm.tsx` and similar forms
    - Replace: All `<input>`, `<label>`, `<textarea>` elements
    - Use: `Field.Input`, `Field.Label` from `@components/Shared/Fields`
    - Note: Field components support floating labels and error states
    - Priority: LOW (current implementation works fine)

### Component Refactoring - UI Elements

14. **Replace SVG icons with FontAwesome icons**
    - ✅ Replaced inline SVG with FontAwesome icons in CollapsibleSection (faChevronDown)
    - ✅ Replaced inline SVG with FontAwesome icons in FileUpload (faCloudArrowUp, faCircleCheck, faXmark)
    - Files: `src/components/Admin/CollapsibleSection.tsx`, `src/components/Admin/FileUpload.tsx`

15. **Replace raw buttons with Button component**
    - ✅ Replaced raw `<button>` with `<Button theme={false}>` in CollapsibleSection
    - File: `src/components/Admin/CollapsibleSection.tsx`

16. **Replace custom table markup with existing Table component**
    - Location: `src/components/Admin/InstancesTable.tsx` (line 29+)
    - Location: `src/components/Admin/TemplatesTable.tsx` (similar structure)
    - Replace: `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` elements
    - Use: `Table`, `Table.Header`, `Table.Body`, `Table.Row`, `Table.Head`, `Table.Cell`
    - Reference: `src/components/Shared/Table/Table.tsx`
    - **NOTE**: Existing Table uses CSS Grid layout (`display: grid`, `contents`) which is incompatible with current striped row styling. Would require significant CSS refactoring. Deferring this as LOW priority.

### Type System Refactoring

17. **Move Template and InstalledApp types to apps.ts**
    - ✅ Moved `Template`, `InstalledApp`, and `UnimportedInstance` types from admin.ts to apps.ts
    - ✅ Consolidated all app-related types in one location
    - Files: `src/types/apps.ts`, `src/types/admin.ts`

18. **Remove duplicate Toast types**
    - ✅ Removed `ToastType` and `Toast` types from admin.ts
    - Reason: Already defined in `toast.feature.tsx`
    - File: `src/types/admin.ts`

19. **Convert request/response types from snake_case to camelCase**
    - Location: `src/types/admin.ts`
    - Types to update:
      - `ImportTemplateRequest` (lines 6-19)
      - `ImportAppRequest` (lines 22-33)
    - Action: Change field names to camelCase (e.g., `template_name` → `templateName`)
    - Add: Transformer functions to convert between API (snake_case) and frontend (camelCase)
    - Reference: Use `formatToCamelCase` and create `formatToSnakeCase` if needed
    - Priority: MEDIUM (would require updating all form submissions to transform data)

### Lower Priority / Optional

20. **Refactor ImportAppForm to use react-hook-form**
    - Location: `src/components/Admin/ImportAppForm.tsx`
    - Replace: Manual form state with `useForm()` from react-hook-form
    - Remove: `useImmer` usage for form data
    - Priority: MEDIUM (nice to have but not blocking)

21. **Implement zod validation schemas**
    - Location: Create `src/components/Admin/schemas.ts` or similar
    - Add: Zod schemas for ImportAppRequest and ImportTemplateRequest
    - Replace: Manual validation logic (e.g., UUID regex check at line 74-80)
    - Priority: MEDIUM (nice to have but not blocking)

22. **Replace manual inputs/labels with Field.Input components**
    - Location: `src/components/Admin/ImportAppForm.tsx` and similar forms
    - Replace: All `<input>`, `<label>`, `<textarea>` elements
    - Use: `Field.Input`, `Field.Label` from `@components/Shared/Fields`
    - Note: Field components support floating labels and error states
    - Priority: LOW (current implementation works fine)

23. **Simplify Image component className logic**
    - Location: `src/components/Shared/Image.tsx` (lines 51-54)
    - Change from: `className={clsx(transition && 'opacity-0...', className)}`
    - Change to: Proper clsx usage as suggested in review comment #2444615663
    - Priority: LOW (not admin-specific)

24. **Optional: Implement useImperativeHandle for CollapsibleSection**
    - Location: `src/components/Admin/CollapsibleSection.tsx`
    - Action: Implement `useImperativeHandle` for controlled state
    - Priority: LOW (marked as optional in review)

---

## File Impact Summary

### Files Modified
- ✅ `src/app/admin/AdminPage.tsx` (partially complete)
- ⏳ `src/app/admin/page.tsx` (needs auth removal)
- ⏳ `src/components/Admin/ImportAppForm.tsx`
- ⏳ `src/components/Admin/ImportTemplateModal.tsx`
- ⏳ `src/components/Admin/CollapsibleSection.tsx`
- ⏳ `src/components/Admin/FileUpload.tsx`
- ⏳ `src/components/Admin/InstancesTable.tsx`
- ⏳ `src/components/Admin/TemplatesTable.tsx`
- ⏳ `src/components/Ui/Layout/LayoutClient.tsx`
- ⏳ `src/components/Shared/Image.tsx`
- ⏳ `src/types/admin.ts` (refactor and move)
- ⏳ `src/types/app.ts` (receive types from admin.ts)
- ⏳ `src/utils/helpers/request.ts`

### Files to Delete
- `src/app/api/admin/apps/import/route.ts`
- `src/app/api/admin/templates/import/route.ts`
- `src/components/Admin/Toast.tsx`
- `src/components/Admin/ToastContainer.tsx`
- `src/components/Providers/SessionProvider.tsx`
- `src/utils/helpers/isAdmin.ts`

### Files to Create
- `src/components/Admin/schemas.ts` (Zod validation schemas)
- `src/utils/formatters/formatToSnakeCase.ts` (if needed for API requests)

---

## Dependencies Check

Verify these packages are installed:
- ✅ `react-hook-form` - For form state management
- ✅ `zod` - For validation schemas
- ✅ `@hookform/resolvers` - To integrate Zod with react-hook-form

---

## Testing Checklist (After Completion)

- [ ] Run `npm run lint:ts` - No TypeScript errors
- [ ] Run `npm run lint:eslint` - No ESLint errors
- [ ] Test admin page loads without auth issues
- [ ] Test template import functionality
- [ ] Test app instance import functionality
- [ ] Test delete functionality for templates and instances
- [ ] Verify toast notifications appear correctly
- [ ] Verify modal interactions work properly
- [ ] Test form validation with zod schemas
- [ ] Verify refresh button updates data

---

## Notes

- The middleware already handles admin access checking (lines 57-70 in `src/middleware.ts`)
- The existing Modal component uses a ref pattern with imperative handle, which is already being used correctly in ConfirmationModal
- The review suggests using `Modal` with trigger pattern: `<Modal content={<Content />}><Button>Open</Button></Modal>`
- Field components are available at `@components/Shared/Fields` and support floating labels
- Table components follow a compound pattern: `Table.Header`, `Table.Row`, etc.

---

## Summary Statistics

### Code Reduction
- **Files deleted**: 4 total
  - 2 API route files (apps/import, templates/import)
  - 2 modal wrapper components (ImportTemplateModal, ImportAppModal)
  - SessionProvider and providers directory
- **Net lines removed**: ~460 lines
- **Modal state complexity**: Reduced from 5 complex state objects to 3 simple data variables

### Commits Made
1. Refactor admin panel and fix template instance relationship logic
2. Refactor admin UI components and type system
3. Fix delete app instance to use app_id instead of id
4. Simplify modal management using trigger pattern
5. Remove isOpen state from all modal management

---

## Last Updated
2025-01-21 - Completed all high-priority refactoring including modal simplification
