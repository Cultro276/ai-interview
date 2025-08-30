# UI Components Documentation

Bu klasör, AI Interview uygulamasının tüm UI componentlerini organize bir şekilde içerir.

## 📁 Klasör Yapısı

```
components/ui/
├── basic/           # Temel UI componentleri
├── enhanced/        # Gelişmiş özellikli componentler  
├── primitives/      # Radix-based primitive componentler
├── utils/           # Utility fonksiyonları ve karmaşık componentler
└── index.ts         # Ana export dosyası
```

## 🎯 Component Kategorileri

### 📦 Basic Components (`/basic/`)
Temel, basit UI componentleri. Hızlı prototyping ve standart kullanım için ideal.

- **Button** - Standart button komponenti
- **Card** - Basit card layout (Header, Content, Footer)
- **Input** - Temel input alanı
- **Badge** - Durum gösterici badge
- **Progress** - İlerleme çubuğu
- **Loader** - Spinner loading göstergesi
- **Skeleton** - Placeholder loading animasyonu
- **EmptyState** - Boş durum gösterimi
- **Steps** - Adım gösterici

### ⚡ Enhanced Components (`/enhanced/`)
Gelişmiş özellikli, theme desteği olan componentler. Production kulımı için optimize edilmiş.

- **AdvancedButton** - Gelişmiş button (loading, animasyonlar, gradient)
- **AdvancedCard** - Gelişmiş card (variant'lar, badge, loading)
- **ResponsiveLayout** - Responsive layout utility'leri

### 🧩 Primitive Components (`/primitives/`)
Radix UI tabanlı, accessibility-first componentler.

- **Dialog** - Modal dialog sistemi
- **DropdownMenu** - Dropdown menü
- **Select** - Select input
- **Separator** - Ayırıcı çizgi
- **Label** - Form label
- **Tooltip** - Hover tooltip

### 🛠️ Utils (`/utils/`)
Utility fonksiyonları ve karmaşık chart componentleri.

- **cn** - Optimized className merger (clsx + tailwind-merge)
- **Charts** - Chart.js tabanlı chart componentleri

## 📖 Kullanım Örnekleri

### Basit Import
```tsx
import { Button, Card, Input } from '@/components/ui';
```

### Kategorize Import
```tsx
import { Button } from '@/components/ui/basic';
import { AdvancedButton } from '@/components/ui/enhanced';
import { Dialog } from '@/components/ui/primitives';
import { cn } from '@/components/ui/utils';
```

### Specific Import
```tsx
import { 
  Button, 
  Card, 
  AdvancedButton, 
  Dialog 
} from '@/components/ui';
```

## 🎨 Component Variants

### Basic vs Enhanced
- **Basic**: Hızlı development, minimal özellikler
- **Enhanced**: Production-ready, theme support, advanced features

### Naming Convention
- Basic components: `Button`, `Card`, `Input`
- Enhanced components: `AdvancedButton`, `AdvancedCard`
- Primitives: lowercase filenames (`dialog.tsx`)

## 🔧 Development Guidelines

### 1. Yeni Component Ekleme
```tsx
// basic/ klasöründe yeni component
export const NewComponent = ({ ...props }) => {
  return <div className={cn('base-styles', className)} {...props} />
}

// index.ts'e ekle
export { NewComponent } from './NewComponent';
```

### 2. Styling
- `cn()` utility'sini kullan
- Tailwind CSS class'ları
- Dark mode desteği

### 3. TypeScript
- Proper interface tanımları
- forwardRef kullanımı
- DisplayName ataması

## 🚀 Özellikler

✅ **Organizasyon**: Kategorize klasör yapısı  
✅ **TypeScript**: Full type safety  
✅ **Accessibility**: Radix UI primitives  
✅ **Responsive**: Mobile-first design  
✅ **Dark Mode**: Theme support  
✅ **Performance**: Optimized imports  
✅ **Developer Experience**: Clear exports ve documentation  

## 📚 Referanslar

- [Radix UI](https://www.radix-ui.com/) - Primitive components
- [Tailwind CSS](https://tailwindcss.com/) - Styling
- [clsx](https://github.com/lukeed/clsx) - Conditional classes
- [Tailwind Merge](https://github.com/dcastil/tailwind-merge) - Class merging
