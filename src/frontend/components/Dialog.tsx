import {
  Children,
  cloneElement,
  isValidElement,
  useEffect,
  useId,
  useRef,
  type ReactElement,
  type ReactNode,
} from 'react';

export function Dialog({
  title,
  close,
  children,
}: {
  title: string;
  close: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const id = useId();
  useEffect(() => {
    const dialog = ref.current;
    dialog?.showModal();
    return () => dialog?.close();
  }, []);
  return (
    <dialog
      ref={ref}
      aria-labelledby={id}
      onCancel={(event) => {
        event.preventDefault();
        close();
      }}
    >
      <div className="dialog-heading">
        <h2 id={id}>{title}</h2>
        <button type="button" onClick={close} aria-label="Close dialog">
          ×
        </button>
      </div>
      {children}
    </dialog>
  );
}

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {Children.map(children, (child) =>
        isValidElement(child) &&
        typeof child.type === 'string' &&
        ['input', 'select', 'textarea'].includes(child.type)
          ? cloneElement(child as ReactElement<{ id?: string }>, { id })
          : child,
      )}
    </div>
  );
}
