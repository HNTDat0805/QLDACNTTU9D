export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t px-4 py-5 sm:px-6">
      <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-2 text-center sm:flex-row sm:text-left">
        <p className="text-muted-foreground text-sm">
          FixCare · Quản lý sửa chữa điện thoại
        </p>
        <p className="text-muted-foreground text-sm">© {currentYear} FixCare</p>
      </div>
    </footer>
  )
}
