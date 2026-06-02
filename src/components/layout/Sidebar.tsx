'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'

const navItems = [
  { href: '/dashboard', label: 'Хяналтын самбар', icon: '⊞' },
  { href: '/patients', label: 'Өвчтөнүүд', icon: '👤' },
  { href: '/cases', label: 'Тохиолдлууд', icon: '📋' },
  { href: '/admin', label: 'Админ', icon: '⚙' },
  { href: '/audit', label: 'Audit Log', icon: '🔍' },
]

const currentUser = {
  name: 'Эмч',
  specialty: 'Clinical user',
}

export default function Sidebar() {
  const pathname = usePathname()
  return (
    <aside className="w-60 min-h-screen bg-slate-900 flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-6 py-5 border-b border-slate-700">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-blue-500 flex items-center justify-center text-white font-bold text-sm">M</div>
          <div>
            <div className="text-white font-semibold text-sm">MedCore</div>
            <div className="text-slate-400 text-xs">Clinical AI</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {navItems.map((item) => {
          const active = pathname.startsWith(item.href)
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                active
                  ? 'bg-blue-600 text-white'
                  : 'text-slate-300 hover:bg-slate-800 hover:text-white'
              }`}
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </Link>
          )
        })}
      </nav>

      {/* User */}
      <div className="px-3 py-4 border-t border-slate-700">
        <div className="flex items-center gap-3 px-3 py-2">
          <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-bold shrink-0">
            {currentUser.name.charAt(0)}
          </div>
          <div className="min-w-0">
            <div className="text-white text-xs font-medium truncate">{currentUser.name}</div>
            <div className="text-slate-400 text-xs truncate">{currentUser.specialty}</div>
          </div>
        </div>
        <Link
          href="/"
          className="mt-2 flex items-center gap-3 px-3 py-2 text-slate-400 hover:text-white text-xs rounded-lg hover:bg-slate-800 transition-colors"
        >
          <span>→</span> Гарах
        </Link>
      </div>
    </aside>
  )
}
