import React from "react"
import { router } from "expo-router"
import { View, Text, Pressable, TextInput } from "react-native"
import type { RiskLevel } from "../lib/types"
import { ChevronLeft } from "lucide-react-native"

function cx(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(" ")
}

export function Card({
  children,
  className,
  onPress,
}: {
  children?: React.ReactNode
  className?: string
  onPress?: () => void
}) {

  const content = (
    <View
      className={cx(
        "rounded-2xl border border-border bg-card p-4",
        className
      )}
    >
      {children}
    </View>
  )

  if (onPress) {
    return <Pressable onPress={onPress}>{content}</Pressable>
  }

  return content
}

export function RiskBadge({
  riskLevel,
  size = "md",
  className,
}: {
  riskLevel: RiskLevel
  size?: "sm" | "md" | "lg"
  className?: string
}) {
  const styles = {
    safe: "bg-green-100 text-green-700",
    suspicious: "bg-amber-100 text-amber-700",
    malicious: "bg-red-100 text-red-700",
  }

  const labels = {
    safe: "Safe",
    suspicious: "Suspicious",
    malicious: "Malicious",
  }

  const sizes = {
    sm: "px-2 py-0.5 text-xs",
    md: "px-3 py-1 text-sm",
    lg: "px-4 py-1.5 text-base",
  }

  return (
    <View className={cx("self-start rounded-full", styles[riskLevel].split(" ")[0], className)}>
      <Text className={cx("font-semibold", styles[riskLevel].split(" ")[1], sizes[size])}>
        {labels[riskLevel]}
      </Text>
    </View>
  )
}

export function AppButton({
  children,
  variant = "primary",
  size = "md",
  fullWidth,
  className,
  onPress,
}: {
  children: React.ReactNode
  variant?: "primary" | "secondary" | "outline" | "ghost"
  size?: "sm" | "md" | "lg"
  fullWidth?: boolean
  className?: string
  onPress?: () => void
}) {
  const variants = {
    primary: {
      container: "bg-primary",
      text: "text-primary-foreground",
    },
    secondary: {
      container: "bg-secondary",
      text: "text-secondary-foreground",
    },
    outline: {
      container: "border-2 border-border bg-transparent",
      text: "text-foreground",
    },
    ghost: {
      container: "bg-transparent",
      text: "text-foreground",
    },
  }

  const sizes = {
    sm: "px-3 py-2",
    md: "px-4 py-3",
    lg: "px-6 py-4",
  }

  const textSizes = {
    sm: "text-sm",
    md: "text-base",
    lg: "text-lg",
  }

  return (
    <Pressable
      onPress={onPress}
      className={cx(
        "items-center justify-center rounded-xl",
        variants[variant].container,
        sizes[size],
        fullWidth && "w-full",
        className
      )}
    >
      <Text className={cx("font-semibold", variants[variant].text, textSizes[size])}>
        {children}
      </Text>
    </Pressable>
  )
}

export function InputField({
  label,
  placeholder,
  value,
  className,
  secureTextEntry,
  onChangeText,
}: {
  label?: string
  placeholder?: string
  value?: string
  className?: string
  secureTextEntry?: boolean
  onChangeText?: (text: string) => void
}) {
  return (
    <View className={cx("gap-1.5", className)}>
      {label ? <Text className="text-sm font-medium text-foreground">{label}</Text> : null}

      <TextInput
        value={value}
        placeholder={placeholder}
        placeholderTextColor="#9CA3AF"
        secureTextEntry={secureTextEntry}
        onChangeText={onChangeText}
        className="w-full rounded-xl border border-input bg-card px-4 py-3 text-base text-foreground"
      />
    </View>
  )
}

export function ListItem({
  title,
  subtitle,
  leftIcon,
  rightElement,
  className,
  onPress,
}: {
  title: string
  subtitle?: string
  leftIcon?: React.ReactNode
  rightElement?: React.ReactNode
  className?: string
  onPress?: () => void
}) {

  return (
    <Pressable
      onPress={onPress}
      className={cx(
        "flex-row items-center gap-3 rounded-xl border border-border bg-card px-4 py-3",
        className
      )}
    >
      {leftIcon ? (
        <View className="h-10 w-10 items-center justify-center rounded-full bg-secondary">
          {leftIcon}
        </View>
      ) : null}

      <View className="flex-1">
        <Text className="font-medium text-foreground" numberOfLines={1}>
          {title}
        </Text>
        {subtitle ? (
          <Text className="text-sm text-muted-foreground" numberOfLines={1}>
            {subtitle}
          </Text>
        ) : null}
      </View>

      {rightElement}
    </Pressable>
  )
}

export function SectionHeader({
  title,
  action,
  className,
  onPressAction,
}: {
  title: string
  action?: React.ReactNode
  className?: string
  onPressAction?: () => void
}) {

  return (
    <View className={cx("flex-row items-center justify-between py-2", className)}>
      <Text className="text-lg font-semibold text-foreground">{title}</Text>

      {action ? (
        <Pressable onPress={onPressAction}>
          <View>{action}</View>
        </Pressable>
      ) : null}
    </View>
  )
}

export function ScreenHeader({
  title,
  showBack = true,
  rightAction,
}: {
  title: string
  showBack?: boolean
  rightAction?: React.ReactNode
}) {

  return (
    <View className="flex-row items-center justify-between border-b border-border bg-background px-4 py-3">
      <View className="w-10">
        {showBack ? (
          <Pressable onPress={() => router.back()} className="items-start">
            <ChevronLeft size={24} color="black" />
          </Pressable>
        ) : null}
      </View>

      <Text className="text-lg font-semibold text-foreground">{title}</Text>

      <View className="w-10 items-end">{rightAction}</View>
    </View>
  )
}

export function BottomNav({
  items,
  activeIndex = 0,
}: {
  items: { icon: React.ReactNode; label: string; href: string }[]
  activeIndex?: number
}) {
  return (
    <View className="flex-row items-center justify-around border-t border-border bg-card px-4 py-2">
      {items.map((item, index) => (
        <Pressable
          key={index}
          onPress={() => router.push(item.href)}
          className="items-center gap-1 rounded-xl px-4 py-2"
        >
          <View>{item.icon}</View>
          <Text
            className={cx(
              "text-xs font-medium",
              index === activeIndex ? "text-primary" : "text-muted-foreground"
            )}
          >
            {item.label}
          </Text>
        </Pressable>
      ))}
    </View>
  )
}

export function ConfidenceIndicator({ value }: { value: number }) {
  const getColor = () => {
    if (value >= 80) return "bg-green-500"
    if (value >= 50) return "bg-amber-500"
    return "bg-red-500"
  }

  return (
    <View className="flex-row items-center gap-2">
      <View className="h-2 flex-1 overflow-hidden rounded-full bg-secondary">
        <View
          className={cx("h-full rounded-full", getColor())}
          style={{ width: `${value}%` }}
        />
      </View>
      <Text className="text-sm font-medium text-muted-foreground">{value}%</Text>
    </View>
  )
}

export function TextLink({
  children,
  onPress,
  className,
}: {
  children: React.ReactNode
  onPress?: (() => void)
  className?: string
}) {
  return (
    <Pressable onPress={onPress}>
      <Text className={cx("font-semibold text-primary", className)}>{children}</Text>
    </Pressable>
  )
}