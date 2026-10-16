import { useId } from 'react';

/** Label + input + error/hint, wired for accessibility. Pass a render prop to customize the control. */
export default function Field({ label, error, hint, className = '', children, ...inputProps }) {
  const id = useId();
  const describedBy = error ? `${id}-error` : hint ? `${id}-hint` : undefined;
  const control =
    typeof children === 'function' ? (
      children({ id, 'aria-invalid': Boolean(error), 'aria-describedby': describedBy })
    ) : (
      <input
        id={id}
        className={`field ${error ? 'field-error' : ''}`}
        aria-invalid={Boolean(error)}
        aria-describedby={describedBy}
        {...inputProps}
      />
    );

  return (
    <div className={className}>
      {label && (
        <label htmlFor={id} className="label">
          {label}
        </label>
      )}
      {control}
      {error ? (
        <p id={`${id}-error`} className="mt-1.5 text-sm font-semibold text-brand" role="alert">
          {error}
        </p>
      ) : (
        hint && (
          <p id={`${id}-hint`} className="mt-1.5 text-sm text-ink-faint">
            {hint}
          </p>
        )
      )}
    </div>
  );
}
