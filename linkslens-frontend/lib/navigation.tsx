import { Home, ScanLine, Clock, User } from "lucide-react-native"

export const bottomNavItems = [
  { icon: <Home size={20} />, label: "Home", href: "/home" },
  { icon: <ScanLine size={20} />, label: "Scan", href: "/scan" },
  { icon: <Clock size={20} />, label: "History", href: "/scan-history" },
  { icon: <User size={20} />, label: "Profile", href: "/profile" },
]
