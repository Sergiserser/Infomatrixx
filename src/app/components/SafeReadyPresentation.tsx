import { useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { StepPrep } from './SafeReady';

type SlideType = 'title' | 'goal' | 'app' | 'desktop' | 'security' | 'mobile' | 'thankyou';

interface Link {
  label: string;
  url?: string;
  slideIndex?: number;
  icon: string;
}

interface Slide {
  type: SlideType;
  title: string;
  subtitle?: string;
  description?: string;
  features?: string[];
  details?: string[];
  screen?: 'home' | 'kit' | 'sos' | 'plan' | 'settings';
  theme?: 'modern' | 'bold' | 'calm' | 'vibrant';
  contact?: string;
  highlights?: string[];
  links?: Link[];
}

export function SafeReadyPresentation() {
  const [currentSlide, setCurrentSlide] = useState(0);

  const colorScheme = {
    primary: 'from-blue-600 to-purple-600',
    accent: 'blue',
    bg: 'from-gray-900 via-blue-900 to-purple-900'
  };

  const slides: Slide[] = [
    // Slide 1: Title/Introduction
    {
      type: 'title',
      title: 'StepPrep',
      subtitle: 'Rescue App',
      description: 'Your comprehensive solution for disaster readiness and emergency response. Be prepared for any situation with intelligent monitoring, real-time alerts, and complete emergency management tools.',
      features: [
        '🏠 Task Management - Track preparedness checklist with progress monitoring',
        '📦 Supply Kit Tracking - Monitor inventory, expiration dates, and stock levels',
        '📞 Emergency Contacts - Quick access to critical contacts and SOS alerts',
        '🗺️ Evacuation Planning - Pre-planned routes and shelter locations',
        '📹 Real-time Monitoring - Camera, microphone, and gesture detection',
        '🌍 Multi-language Support - Available in English and Ukrainian'
      ],
      links: [
        { label: 'Our Goal', slideIndex: 1, icon: '🎯' },
        { label: 'Features', slideIndex: 2, icon: '🏠' },
        { label: 'Desktop System', slideIndex: 5, icon: '💻' },
        { label: 'Business Use', slideIndex: 6, icon: '🔒' }
      ]
    },
    // Slide 2: Our Goal
    {
      type: 'goal',
      title: 'Our Goal',
      subtitle: 'Maximum Safety & Rapid Emergency Response',
      description: 'Our main goal is to ensure maximum safety for users and a quick response to emergency situations, such as cases of gun violence, domestic violence, and the maximum efficiency of transmitting information about these cases to representatives of the rescue team in order to ensure maximum efficiency in providing assistance to our audience.',
      features: [
        '🛡️ Maximum User Safety - Proactive protection through AI-powered threat detection and real-time monitoring systems',
        '⚡ Rapid Emergency Response - Instant alert transmission to rescue teams with critical situation details',
        '🔫 Gun Violence Detection - Advanced audio and visual recognition to identify firearm-related threats',
        '🏠 Domestic Violence Protection - Discrete monitoring and quick-access emergency alerts for vulnerable individuals',
        '📡 Efficient Information Transmission - Streamlined communication channels with rescue teams and emergency services',
        '🎯 Targeted Assistance - Precise location data and situation context to ensure fast, effective help delivery'
      ]
    },
    // Slide 3: Home Screen - Task Management
    {
      type: 'app',
      title: 'Stay Organized with Tasks',
      description: 'Track your preparedness checklist and monitor your readiness progress. Complete essential tasks like checking water supply, testing emergency equipment, and rotating food stock. Visual progress indicators show your overall readiness percentage.',
      details: [
        '✓ Check off completed tasks in real-time',
        '✓ Monitor overall readiness percentage',
        '✓ Add custom tasks for your specific needs',
        '✓ Get reminders for important preparations'
      ],
      screen: 'home' as const,
      theme: 'modern' as const
    },
    // Slide 4: Kit Screen - Supply Management
    {
      type: 'app',
      title: 'Manage Your Emergency Kit',
      description: 'Keep track of essential supplies, expiration dates, and inventory status. Ensure you always have critical items like water, first aid supplies, medications, and emergency tools ready when you need them most.',
      details: [
        '✓ Track quantity and expiration dates',
        '✓ Color-coded status indicators (OK, Low, Expired)',
        '✓ Add new items with custom details',
        '✓ Receive alerts for missing or expired items'
      ],
      screen: 'kit' as const,
      theme: 'calm' as const
    },
    // Slide 5: SOS Screen - Emergency Contacts
    {
      type: 'app',
      title: 'Quick Access to Help',
      description: 'One-tap SOS alerts and instant access to emergency contacts. Reach emergency services, family members, and medical contacts immediately during critical situations. The large SOS button ensures help is always just one tap away.',
      details: [
        '✓ Large emergency SOS button for instant alerts',
        '✓ Quick-dial emergency services (911, local contacts)',
        '✓ Store family and medical emergency contacts',
        '✓ Send location data with SOS alerts'
      ],
      screen: 'sos' as const,
      theme: 'bold' as const
    },
    // Slide 6: Desktop Version - Main Monitoring System
    {
      type: 'desktop',
      title: 'Desktop Version - Main Monitoring System',
      description: 'The desktop version serves as the primary monitoring system, using advanced multi-sensor detection to identify emergency situations in real-time. Organized through a comprehensive multi-tab interface for complete safety management.',
      features: [
        '🎥 Multi-Sensor Detection - Camera, microphone, and gesture tracking detect sudden motion, body hits/collisions, bright flashes, sharp impulse sounds, sustained loud sounds, and manual help gestures',
        '📊 Monitoring Tab - Live camera view with real-time risk score calculation, alarm status display, detected movement tracking, gesture information, and emergency contact number visibility',
        '🗺️ Shelter Tab - Automatic nearby metro shelter search using geolocation and OpenStreetMap/Overpass API, displays shelter candidates, and opens Google Maps for route navigation without requiring API keys',
        '🎒 Go Bag Tab - Fully editable emergency supplies checklist where users can customize, add, remove, and save essential evacuation items for quick preparation',
        '⚙️ Settings Tab - Complete configuration hub for language selection (Ukrainian/English), emergency contact management, location settings, Google account integration, and shelter search parameters',
        '💾 Evidence Capture System - Automatic saving of images and event metadata when alarms trigger, creating a documented record for later review and emergency response analysis',
        '🧪 Demo Mode - Safe testing environment enabled by default, allowing users to test alarms, detection systems, shelter search, and all interface features without triggering real emergency calls',
        '🌍 Full Localization Support - Complete Ukrainian and English language support across all interface buttons, labels, status messages, shelter search prompts, and emergency information'
      ]
    },
    // Slide 7: Desktop Security Applications for Businesses
    {
      type: 'security',
      title: 'Desktop Security Applications',
      description: 'The desktop version is highly recommended for local businesses and commercial establishments. It provides professional-grade security monitoring that can significantly enhance safety and prevent incidents.',
      features: [
        '🍺 Bars & Nightclubs - Monitor for violent altercations, suspicious behavior, and emergency situations with automatic threat detection and evidence recording for security teams',
        '🏪 Supermarkets & Retail Stores - Integrate with existing camera systems to detect shoplifting, violent incidents, customer distress signals, and provide immediate security response',
        '🏬 Mini-Markets & Convenience Stores - Protect staff and customers with 24/7 monitoring, robbery detection, and instant emergency alert transmission to law enforcement',
        '🎥 Multi-Camera Integration - Connect multiple camera feeds from different areas of your establishment for comprehensive coverage and synchronized monitoring',
        '👮 Security Team Enhancement - Provide security personnel with AI-assisted threat detection, reducing response time and improving incident prevention capabilities',
        '📹 Legal Evidence Documentation - Automatic recording and timestamping of security incidents creates admissible evidence for insurance claims and legal proceedings',
        '⚡ Real-time Alert System - Instant notifications to security staff, management, and emergency services when threats are detected, enabling rapid intervention',
        '💼 Business Protection - Reduce liability, prevent losses, protect employees and customers, and maintain a safer business environment with continuous AI monitoring'
      ]
    },
    // Slide 8: Mobile Version - Quick Emergency Access
    {
      type: 'mobile',
      title: 'Mobile Version - Quick Emergency Access',
      description: 'The mobile version provides a simplified rescue interface optimized for phone use. Designed for rapid emergency response with essential features accessible on-the-go from any mobile device.',
      features: [
        '🚨 Emergency SOS Button - Large, accessible panic button for instant emergency alerts and immediate help requests',
        '📞 Emergency Contact Dialing - Quick-dial access to pre-configured emergency contacts with one-tap calling functionality',
        '🗺️ Shelter Feed - Mobile-optimized shelter location display with nearby safe zones and evacuation points',
        '📍 GPS Support - Real-time location tracking and sharing for accurate emergency response coordination',
        '👤 Google Account Registration - Seamless account integration for data synchronization and backup across devices',
        '⚙️ Settings Screen - Mobile-friendly configuration for emergency contacts, language preferences, and notification settings',
        '🎒 Go-Bag List - Portable checklist access allowing users to verify emergency supplies from anywhere',
        '🌍 Full Localization - Complete Ukrainian and English support for all mobile interface elements and emergency communications'
      ]
    },
    // Slide 9: Thank You
    {
      type: 'thankyou',
      title: 'Thank You for Your Attention',
      subtitle: 'Stay Safe. Stay Ready.',
      contact: 'StepPrep - Emergency Preparedness Made Simple',
      highlights: [
        'Mobile & Desktop Support',
        'Real-time AI Monitoring',
        'Business Security Ready',
        'Multi-language Support (EN/UK)'
      ],
      links: [
        { label: 'Back to Start', slideIndex: 0, icon: '🏠' },
        { label: 'View Features', slideIndex: 2, icon: '📱' },
        { label: 'Security Info', slideIndex: 6, icon: '🔒' }
      ]
    }
  ];

  const nextSlide = () => {
    if (currentSlide < slides.length - 1) {
      setCurrentSlide(currentSlide + 1);
    }
  };

  const prevSlide = () => {
    if (currentSlide > 0) {
      setCurrentSlide(currentSlide - 1);
    }
  };

  const slide = slides[currentSlide];

  return (
    <div className="min-h-screen w-full bg-black flex items-center justify-center">
      <div className="w-full h-screen max-w-[1920px] max-h-[1080px] relative flex flex-col overflow-hidden" style={{ aspectRatio: '16 / 9' }}>
        {/* Animated Background */}
        <div className="absolute inset-0 bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
          <div className="absolute inset-0 opacity-30">
            <div className="absolute top-0 left-0 w-96 h-96 bg-blue-500 rounded-full mix-blend-multiply filter blur-3xl animate-blob"></div>
            <div className="absolute top-0 right-0 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-2000"></div>
            <div className="absolute bottom-0 left-1/2 w-96 h-96 bg-pink-500 rounded-full mix-blend-multiply filter blur-3xl animate-blob animation-delay-4000"></div>
          </div>
        </div>

        {/* Slide Content */}
        <div key={currentSlide} className="flex-1 flex items-center justify-center px-16 py-8 relative z-10 slide-transition overflow-y-auto">
        {slide.type === 'title' && (
          <div className="text-center max-w-6xl animate-fade-in">
            <h1 className="text-6xl font-bold text-white mb-4 animate-slide-down">{slide.title}</h1>
            <p className="text-3xl text-blue-400 mb-6 animate-slide-down animation-delay-200">{slide.subtitle}</p>
            <p className="text-lg text-gray-300 mb-6 max-w-4xl mx-auto leading-relaxed animate-fade-in animation-delay-400">{slide.description}</p>

            {/* Hyperlink Buttons */}
            {slide.links && (
              <div className="flex gap-3 justify-center mb-6 animate-fade-in animation-delay-600">
                {slide.links.map((link, idx) => (
                  link.slideIndex !== undefined ? (
                    <button
                      key={idx}
                      onClick={() => setCurrentSlide(link.slideIndex!)}
                      className={`flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r ${colorScheme.primary} text-white rounded-lg font-semibold hover:scale-110 hover:shadow-2xl hover:shadow-${colorScheme.accent}-500/50 transition-all duration-300 animate-bounce-in text-sm`}
                      style={{ animationDelay: `${700 + idx * 150}ms` }}
                    >
                      <span className="text-lg">{link.icon}</span>
                      <span>{link.label}</span>
                    </button>
                  ) : (
                    <a
                      key={idx}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r ${colorScheme.primary} text-white rounded-lg font-semibold hover:scale-110 hover:shadow-2xl hover:shadow-${colorScheme.accent}-500/50 transition-all duration-300 animate-bounce-in text-sm`}
                      style={{ animationDelay: `${700 + idx * 150}ms` }}
                    >
                      <span className="text-lg">{link.icon}</span>
                      <span>{link.label}</span>
                    </a>
                  )
                ))}
              </div>
            )}

            <div className="grid grid-cols-2 gap-4 max-w-5xl mx-auto">
              {slide.features?.map((feature, idx) => (
                <div
                  key={idx}
                  className="bg-gray-800/80 backdrop-blur-sm rounded-lg p-4 text-left text-sm text-gray-200 hover:bg-gray-700/90 hover:scale-105 hover:shadow-xl transition-all duration-300 border-l-4 border-blue-500 animate-slide-up"
                  style={{ animationDelay: `${1000 + idx * 100}ms` }}
                >
                  {feature}
                </div>
              ))}
            </div>
          </div>
        )}

        {slide.type === 'goal' && (
          <div className="text-center max-w-6xl animate-fade-in">
            <div className="text-5xl mb-4 animate-bounce-in">🎯</div>
            <h1 className="text-5xl font-bold text-white mb-4 animate-slide-down">{slide.title}</h1>
            <p className="text-2xl text-red-400 mb-6 font-semibold animate-slide-down animation-delay-200">{slide.subtitle}</p>
            <div className="bg-gray-800/80 backdrop-blur-sm rounded-2xl p-6 mb-6 border-2 border-red-500 animate-fade-in animation-delay-400 hover:border-red-400 hover:shadow-2xl hover:shadow-red-500/50 transition-all duration-300">
              <p className="text-base text-gray-200 leading-relaxed max-w-5xl mx-auto">
                {slide.description}
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4 max-w-5xl mx-auto">
              {slide.features?.map((feature, idx) => (
                <div
                  key={idx}
                  className="bg-gray-800/80 backdrop-blur-sm rounded-lg p-4 text-left text-sm text-gray-200 hover:bg-gray-700/90 hover:scale-105 hover:shadow-xl transition-all duration-300 border-l-4 border-red-500 animate-slide-up"
                  style={{ animationDelay: `${600 + idx * 100}ms` }}
                >
                  {feature}
                </div>
              ))}
            </div>
          </div>
        )}

        {slide.type === 'app' && (
          <div className="flex gap-8 items-center max-w-7xl w-full">
            {/* Left: Description */}
            <div className="flex-1 text-left animate-slide-right">
              <h2 className="text-4xl font-bold text-white mb-4">{slide.title}</h2>
              <p className="text-base text-gray-300 leading-relaxed mb-6 animate-fade-in animation-delay-200">
                {slide.description}
              </p>
              {slide.details && (
                <div className="space-y-2">
                  {slide.details.map((detail, idx) => (
                    <div
                      key={idx}
                      className="bg-gray-800/80 backdrop-blur-sm rounded-lg p-3 text-sm text-gray-200 border-l-4 border-blue-500 hover:bg-gray-700/90 hover:translate-x-2 transition-all duration-300 animate-slide-right"
                      style={{ animationDelay: `${400 + idx * 100}ms` }}
                    >
                      {detail}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Right: App Preview */}
            <div className="flex-shrink-0 animate-slide-left">
              <div className="bg-white rounded-3xl shadow-2xl overflow-hidden hover:scale-105 hover:shadow-blue-500/50 transition-all duration-500" style={{ width: '320px', height: '560px' }}>
                <StepPrep
                  initialScreen={slide.screen}
                  initialTheme={slide.theme}
                  showThemeSwitcher={false}
                />
              </div>
            </div>
          </div>
        )}

        {slide.type === 'desktop' && (
          <div className="max-w-6xl w-full animate-fade-in">
            <h2 className="text-4xl font-bold text-white mb-4 text-center animate-slide-down">{slide.title}</h2>
            <p className="text-base text-gray-300 mb-6 text-center max-w-4xl mx-auto leading-relaxed animate-fade-in animation-delay-200">{slide.description}</p>
            <div className="grid grid-cols-2 gap-3">
              {slide.features?.map((feature, idx) => (
                <div
                  key={idx}
                  className="bg-gray-800/80 backdrop-blur-sm rounded-lg p-3 text-sm text-gray-200 hover:bg-gray-700/90 hover:scale-105 hover:shadow-xl transition-all duration-300 border-l-4 border-blue-500 animate-slide-up"
                  style={{ animationDelay: `${400 + idx * 100}ms` }}
                >
                  {feature}
                </div>
              ))}
            </div>
          </div>
        )}

        {slide.type === 'security' && (
          <div className="max-w-6xl w-full animate-fade-in">
            <div className="text-5xl mb-4 text-center animate-bounce-in">🔒</div>
            <h2 className="text-4xl font-bold text-white mb-4 text-center animate-slide-down animation-delay-200">{slide.title}</h2>
            <p className="text-base text-gray-300 mb-6 text-center max-w-4xl mx-auto leading-relaxed animate-fade-in animation-delay-400">{slide.description}</p>
            <div className="grid grid-cols-2 gap-3">
              {slide.features?.map((feature, idx) => (
                <div
                  key={idx}
                  className="bg-gray-800/80 backdrop-blur-sm rounded-lg p-3 text-sm text-gray-200 hover:bg-purple-900/50 hover:scale-105 hover:shadow-xl hover:shadow-purple-500/30 transition-all duration-300 border-l-4 border-purple-500 animate-slide-up"
                  style={{ animationDelay: `${600 + idx * 100}ms` }}
                >
                  {feature}
                </div>
              ))}
            </div>
          </div>
        )}

        {slide.type === 'mobile' && (
          <div className="max-w-6xl w-full animate-fade-in">
            <h2 className="text-4xl font-bold text-white mb-4 text-center animate-slide-down">{slide.title}</h2>
            <p className="text-base text-gray-300 mb-6 text-center max-w-4xl mx-auto leading-relaxed animate-fade-in animation-delay-200">{slide.description}</p>
            <div className="grid grid-cols-2 gap-3">
              {slide.features?.map((feature, idx) => (
                <div
                  key={idx}
                  className="bg-gray-800/80 backdrop-blur-sm rounded-lg p-3 text-sm text-gray-200 hover:bg-green-900/50 hover:scale-105 hover:shadow-xl hover:shadow-green-500/30 transition-all duration-300 border-l-4 border-green-500 animate-slide-up"
                  style={{ animationDelay: `${400 + idx * 100}ms` }}
                >
                  {feature}
                </div>
              ))}
            </div>
          </div>
        )}

        {slide.type === 'thankyou' && (
          <div className="text-center max-w-4xl animate-fade-in">
            <h1 className="text-5xl font-bold text-white mb-6 animate-slide-down">{slide.title}</h1>
            <p className="text-3xl text-blue-400 mb-8 animate-slide-down animation-delay-200">{slide.subtitle}</p>

            {slide.highlights && (
              <div className="grid grid-cols-2 gap-3 mb-8 max-w-3xl mx-auto">
                {slide.highlights.map((highlight, idx) => (
                  <div
                    key={idx}
                    className="bg-gray-800/80 backdrop-blur-sm rounded-lg p-3 text-base text-white border-2 border-blue-500 hover:bg-gray-700/90 hover:scale-110 hover:shadow-2xl hover:shadow-blue-500/50 transition-all duration-300 animate-slide-up"
                    style={{ animationDelay: `${400 + idx * 150}ms` }}
                  >
                    {highlight}
                  </div>
                ))}
              </div>
            )}

            {/* Hyperlink Buttons */}
            {slide.links && (
              <div className="flex gap-3 justify-center mb-6 animate-fade-in animation-delay-1000">
                {slide.links.map((link, idx) => (
                  link.slideIndex !== undefined ? (
                    <button
                      key={idx}
                      onClick={() => setCurrentSlide(link.slideIndex!)}
                      className={`flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r ${colorScheme.primary} text-white rounded-lg font-semibold hover:scale-110 hover:shadow-2xl transition-all duration-300 text-sm`}
                    >
                      <span className="text-lg">{link.icon}</span>
                      <span>{link.label}</span>
                    </button>
                  ) : (
                    <a
                      key={idx}
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r ${colorScheme.primary} text-white rounded-lg font-semibold hover:scale-110 hover:shadow-2xl transition-all duration-300 text-sm`}
                    >
                      <span className="text-lg">{link.icon}</span>
                      <span>{link.label}</span>
                    </a>
                  )
                ))}
              </div>
            )}

            <div className="text-lg text-gray-400 mt-6 animate-fade-in animation-delay-1000">
              {slide.contact}
            </div>
            <div className="mt-8 text-6xl animate-bounce-in animation-delay-1200">🛡️</div>
          </div>
        )}
      </div>

        {/* Navigation Controls */}
        <div className="bg-gray-800/90 backdrop-blur-md px-6 py-4 flex items-center justify-between relative z-10 border-t border-gray-700">
          {/* Previous Button */}
          <button
            onClick={prevSlide}
            disabled={currentSlide === 0}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg disabled:opacity-30 disabled:cursor-not-allowed hover:from-blue-500 hover:to-blue-600 hover:scale-105 hover:shadow-lg transition-all duration-300 text-sm"
          >
            <ChevronLeft size={16} />
            Previous
          </button>

          {/* Slide Indicators */}
          <div className="flex items-center gap-2">
            {slides.map((_, idx) => (
              <button
                key={idx}
                onClick={() => setCurrentSlide(idx)}
                className={`rounded-full transition-all duration-300 ${
                  idx === currentSlide
                    ? 'bg-gradient-to-r from-blue-500 to-purple-500 w-6 h-2.5 shadow-lg shadow-blue-500/50'
                    : 'bg-gray-600 w-2.5 h-2.5 hover:bg-gray-500 hover:scale-125'
                }`}
                aria-label={`Go to slide ${idx + 1}`}
              />
            ))}
            <span className="ml-3 text-gray-300 text-xs font-semibold">
              {currentSlide + 1} / {slides.length}
            </span>
          </div>

          {/* Next Button */}
          <button
            onClick={nextSlide}
            disabled={currentSlide === slides.length - 1}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-blue-700 text-white rounded-lg disabled:opacity-30 disabled:cursor-not-allowed hover:from-blue-500 hover:to-blue-600 hover:scale-105 hover:shadow-lg transition-all duration-300 text-sm"
          >
            Next
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Keyboard Navigation Hint */}
        <div className="absolute top-4 right-4 text-gray-300 text-sm bg-gray-800/70 backdrop-blur-sm px-4 py-2 rounded-lg z-20 animate-fade-in">
          ⌨️ Use arrow keys ← → to navigate
        </div>
      </div>
    </div>
  );
}

// Keyboard navigation
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') {
      const nextBtn = document.querySelector('[aria-label*="Next"]') as HTMLButtonElement;
      nextBtn?.click();
    } else if (e.key === 'ArrowLeft') {
      const prevBtn = document.querySelector('[aria-label*="Previous"]') as HTMLButtonElement;
      prevBtn?.click();
    }
  });
}
