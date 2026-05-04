from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import uvicorn
import random
import re
import os
import sqlite3
import hashlib
import secrets
from datetime import date, datetime, timedelta

app = FastAPI(title="FitBot AI — Intelligent Fitness Companion")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

@app.get("/login")
async def serve_login():
    return FileResponse("static/login.html")

@app.get("/admin")
async def serve_admin():
    return FileResponse("static/index.html")

# ---- State ----
user_data = {"age": 30, "weight": 70, "height": 170}
progress_history: List[Dict] = []

# ---- Models ----
class ChatRequest(BaseModel):
    message: str

class PlanRequest(BaseModel):
    age: int
    weight: float
    height: float
    goal: str
    experience: str

# ---- Utilities ----
def body_fat_estimate(weight: float, height: float, age: int) -> float:
    bmi = weight / ((height / 100) ** 2)
    return round(1.20 * bmi + 0.23 * age - 16.2, 1)

def calc_bmi(weight: float, height: float) -> float:
    return round(weight / ((height / 100) ** 2), 1)

def adjust_plan(progress: List[Dict]) -> str:
    if not progress:
        return "📌 Start tracking your workouts to get adaptive recommendations!"
    last = progress[-1]
    if not last.get("workout_done", False):
        return "📉 Consistency needs work → Focus on building habits with shorter, easier sessions."
    return "📈 Great consistency! → Time to increase intensity with progressive overload."

# ---- Smart Chat Engine ----
RESPONSES = {
    # Greetings
    "greeting": [
        "Hey there, champion! 💪 How can I help you crush your fitness goals today?",
        "Hello! 🔥 Ready to level up your fitness? Ask me anything!",
        "Hi! 👋 I'm FitBot, your AI fitness coach. What's on your mind?",
        "Welcome back! 💜 Let's make today count. What do you need help with?",
    ],
    # Weight loss
    "weight_loss": [
        "🔥 For effective weight loss:\n\n1. Create a calorie deficit of 400-600 kcal/day\n2. Prioritize protein (1.6-2.2g per kg bodyweight)\n3. Do 3-4 strength sessions + 2-3 cardio per week\n4. HIIT burns more calories in less time\n5. Sleep 7-9 hours — poor sleep increases hunger hormones\n6. Track your food intake for awareness\n\nConsistency beats perfection! 🎯",
        "💡 The best approach to fat loss:\n\n• Strength train to preserve muscle (3-4x/week)\n• Add walking — aim for 8,000-10,000 steps/day\n• Eat whole foods: lean protein, veggies, complex carbs\n• Reduce liquid calories (sodas, juices, alcohol)\n• Be patient — sustainable loss is 0.5-1kg per week\n\nWant me to generate a custom plan? 📋",
    ],
    # Muscle building
    "muscle_gain": [
        "💪 To build muscle effectively:\n\n1. Progressive overload — increase weight/reps each session\n2. Eat in a calorie surplus of 300-500 kcal/day\n3. Get 1.6-2.2g protein per kg bodyweight\n4. Train each muscle group 2x per week\n5. Focus on compound lifts: Squat, Bench, Deadlift, OHP, Rows\n6. Sleep 7-9 hours for recovery and growth\n\nMuscle is built in the kitchen and during sleep! 🏆",
        "🏋️ Muscle building fundamentals:\n\n• Follow a structured program (Push/Pull/Legs or Upper/Lower)\n• Track your lifts — progressive overload is king\n• Eat enough calories and protein\n• Rest 1-3 min between sets for strength\n• Don't skip leg day! 🦵\n• Be patient — muscle growth takes months, not days\n\nWant a personalized plan? Try the Plan Generator! 📋",
    ],
    # Diet & Nutrition
    "diet": [
        "🥗 Nutrition essentials:\n\n• Protein: 1.6-2.2g/kg — chicken, fish, eggs, legumes, whey\n• Carbs: Fuel your workouts — rice, oats, sweet potatoes, fruits\n• Fats: Don't fear them — avocado, nuts, olive oil (0.8-1g/kg)\n• Vegetables: Eat the rainbow — aim for 5+ servings/day\n• Hydration: Drink 2-3L of water daily 💧\n• Meal timing matters less than total daily intake\n\nConsistency with nutrition > perfection! 🎯",
        "🍽️ Smart eating guidelines:\n\n1. Calculate your TDEE (Total Daily Energy Expenditure)\n2. For fat loss: eat 400-600 below TDEE\n3. For muscle gain: eat 300-500 above TDEE\n4. Prioritize whole, unprocessed foods\n5. Prep meals in advance to stay on track\n6. Don't demonize any food group\n\n80% whole foods + 20% foods you enjoy = sustainable! 💜",
    ],
    # Workout advice
    "workout": [
        "🏋️ Workout fundamentals:\n\n• Warm up: 5-10 min dynamic stretching\n• Compound movements first (squats, deadlifts, bench)\n• Isolation exercises after (curls, lateral raises)\n• Train with proper form — ego lifting = injuries\n• Progressive overload: add weight, reps, or sets over time\n• Cool down with static stretching\n\nConsistency > intensity. Show up every day! 🔥",
        "⚡ Effective training tips:\n\n1. Follow a structured program (don't wing it!)\n2. Train each muscle 2x per week minimum\n3. Use 8-12 rep range for hypertrophy\n4. Rest 60-90s between sets for muscle growth\n5. Track your workouts in a log\n6. Deload every 4-6 weeks\n\nThe best program is one you stick to! 💪",
    ],
    # Supplements
    "supplements": [
        "💊 Evidence-based supplements:\n\n✅ Worth it:\n• Creatine Monohydrate (5g/day) — most researched supplement\n• Whey Protein — convenient way to hit protein goals\n• Vitamin D — if you don't get enough sun\n• Omega-3 Fish Oil — anti-inflammatory benefits\n• Caffeine — improves performance when used wisely\n\n❌ Skip:\n• Fat burners — waste of money\n• BCAAs — unnecessary if eating enough protein\n• Testosterone boosters — don't work\n\nSupplements enhance a good diet, they don't replace it! 🎯",
    ],
    # Sleep & Recovery
    "sleep": [
        "😴 Sleep is a superpower for fitness:\n\n1. Aim for 7-9 hours per night\n2. Keep a consistent sleep schedule\n3. No screens 30-60 min before bed\n4. Keep your room cool (18-20°C) and dark\n5. Avoid caffeine after 2 PM\n6. Magnesium before bed can help\n\nPoor sleep = higher cortisol, more hunger, less recovery. Prioritize it! 🌙",
    ],
    # Motivation
    "motivation": [
        "🔥 \"The only bad workout is the one that didn't happen.\" — You've got this! Every rep counts, every meal matters. Be 1% better today than yesterday. 💪",
        "⚡ \"Discipline is choosing between what you want NOW and what you want MOST.\" — Keep showing up. Your future self will thank you! 🏆",
        "🌟 \"It's not about being the best. It's about being better than you were yesterday.\" — Progress over perfection. Let's GO! 💜",
        "🔥 \"Success isn't always about greatness. It's about consistency.\" — Small daily actions compound into incredible results. Don't quit! 🎯",
        "💪 \"Your body can stand almost anything. It's your mind that you have to convince.\" — Push through. You're stronger than you think! ⚡",
    ],
    # Stretching
    "stretching": [
        "🧘 Stretching guide:\n\n Before workout (Dynamic):\n• Leg swings, arm circles, hip openers\n• Light jogging or jumping jacks\n• Hold each for 10-15 seconds\n\n After workout (Static):\n• Hamstring stretch — 30 seconds each leg\n• Quad stretch — 30 seconds each leg\n• Shoulder stretch — 30 seconds each arm\n• Child's pose — 30-60 seconds\n\nFlexibility reduces injury risk and improves performance! 🎯",
    ],
    # Beginner
    "beginner": [
        "🌱 Welcome to your fitness journey! Here's how to start:\n\n1. Start with 3 full-body workouts per week\n2. Learn proper form before adding weight\n3. Focus on compound movements (squat, push-up, rows)\n4. Walk 20-30 min daily\n5. Clean up your diet gradually — don't go extreme\n6. Get 7-9 hours of sleep\n\nThe first step is the hardest, but you've already taken it! 🏆\n\nTry the Plan Generator for a custom beginner program! 📋",
    ],
    # Rest days
    "rest": [
        "😴 Rest days are GROWTH days:\n\n• Muscles repair and grow during rest, not during training\n• Take 2-3 rest days per week minimum\n• Active recovery: light walking, yoga, swimming\n• Eat enough protein on rest days too\n• Sleep is the best recovery tool\n• Listen to your body — soreness is okay, pain is not\n\nOvertraining leads to injuries and burnout. Rest smart! 🧠",
    ],
    # Cardio
    "cardio": [
        "🏃 Cardio guide:\n\n For Fat Loss:\n• HIIT: 20-30 min, 3x per week (sprints, cycling, rowing)\n• LISS: 30-45 min walking, 4-5x per week\n• Mix both for best results\n\n For Heart Health:\n• 150 min moderate OR 75 min vigorous per week\n• Zone 2 cardio is gold for longevity\n\n For Muscle Gain:\n• Limit cardio to 2-3 sessions per week\n• Don't do cardio before lifting\n\nThe best cardio is the one you enjoy! 🎯",
    ],
    # Water / Hydration
    "hydration": [
        "💧 Hydration guide:\n\n• Drink 2-3 liters of water daily\n• Add 500ml for every hour of exercise\n• Start your day with a glass of water\n• Urine should be light yellow\n• Electrolytes matter during intense exercise (sodium, potassium)\n• Coffee and tea count toward intake\n\nDehydration = reduced performance, cramps, and fatigue! Stay hydrated! 🥤",
    ],
    # Default
    "default": [
        "Great question! 🤔 I can help with:\n\n• 🏋️ Workout plans and exercises\n• 🥗 Diet and nutrition advice\n• 💊 Supplement recommendations\n• 😴 Sleep and recovery tips\n• 🏃 Cardio guidance\n• 🧘 Stretching and flexibility\n• 🔥 Motivation and mindset\n• 🩹 Injury prevention & rehab\n• 🧠 Mental health & wellness\n\nTry asking about any of these topics! 💪",
        "I'd love to help! 💜 Try asking me something like:\n\n• \"How do I lose weight?\"\n• \"Best exercises for muscle gain\"\n• \"What should I eat?\"\n• \"Recommend supplements\"\n• \"How to improve sleep\"\n• \"Help with back pain\"\n• \"Mental health and fitness\"\n\nOr try the quick action buttons above! 🎯",
    ],
    # Injury
    "injury": [
        "🩹 Injury advice:\n\n**General RICE Protocol:**\n• Rest — stop using the injured area\n• Ice — 15-20 min every 2-3 hours (first 48-72h)\n• Compress — reduce swelling with a bandage\n• Elevate — raise the injured area above heart level\n\n**Back Pain:**\n• Strengthen core and glutes — weak hips = back pain\n• Hip flexor and hamstring stretching\n• Avoid heavy deadlifts until pain-free\n• Cat-cow, child's pose, bird-dog are excellent\n\n**Knee Pain:**\n• Strengthen quads and glutes\n• Avoid deep squats until pain subsides\n• Check foot pronation — orthotics can help\n\n⚠️ Persistent or severe pain = see a physiotherapist. Don't train through sharp pain!",
        "🚑 Training around injuries:\n\n• **Work around it** — if your knee hurts, train upper body\n• **Reduce load** — lighter weight, higher reps\n• **Fix the root cause** — most injuries stem from muscle imbalances or poor form\n• **Rehab exercises** are key — they strengthen the weak areas causing pain\n\n**Common fixes:**\n• Shin splints → Strengthen calves, reduce mileage, stretch\n• Shoulder impingement → Face pulls, external rotation work\n• Wrist pain → Wrist circles, reduce pressing volume\n\nAlways consult a physio for serious injuries! 🏥",
    ],
    # Mental Health
    "mental_health": [
        "🧠 Fitness & Mental Health:\n\nExercise is one of the most powerful antidepressants:\n• 30 min of moderate exercise = significant anxiety/depression reduction\n• Releases dopamine, serotonin, endorphins — your brain's happy chemicals\n• Reduces cortisol (stress hormone)\n\n**Mindfulness Tips:**\n• 5 min deep breathing before training — reduces cortisol\n• Meditation apps: Headspace, Calm, Waking Up\n• Journaling after workouts for mental clarity\n• Nature walks — green exercise boosts mood 2x more than gym alone\n\n**Burnout prevention:**\n• Don't train when genuinely exhausted\n• Take deload weeks — physical rest = mental rest\n• Track your mood alongside workouts\n\nYour mental health matters more than any PR. 💜",
        "💆 Stress & Fitness:\n\n• Chronic stress → high cortisol → fat gain + muscle loss\n• Exercise reduces cortisol but very intense training adds more stress\n• If life is stressful → reduce workout intensity, not frequency\n• Yoga and walking are underrated stress-busters\n\n**Quick stress relief:**\n• Box breathing: inhale 4s → hold 4s → exhale 4s → hold 4s\n• Cold shower post-workout (reduces inflammation + boosts alertness)\n• 20 min walk in nature\n• Progressive muscle relaxation before bed\n\nYou can't out-train a stressed mind. Take care of both! 🌿",
    ],
    # Yoga
    "yoga": [
        "🧘 Yoga for Fitness:\n\n**Benefits for gym-goers:**\n• Improves flexibility and range of motion\n• Reduces injury risk significantly\n• Strengthens stabilizing muscles\n• Enhances mind-muscle connection\n• Active recovery on rest days\n\n**Best yoga styles for athletes:**\n• Vinyasa — dynamic, flows well with strength training\n• Yin Yoga — deep tissue, best for recovery days\n• Power Yoga — more strength-based, great for conditioning\n• Hatha — beginner-friendly, slower pace\n\n**Key poses for gym recovery:**\n• Pigeon pose → hips & glutes\n• Downward dog → hamstrings & calves\n• Child's pose → lower back\n• Warrior I & II → hip flexors & quads\n• Cat-Cow → spine mobility\n\nEven 15 min of yoga on rest days = massive benefits! 🙏",
    ],
    # Posture
    "posture": [
        "🦴 Fix Your Posture:\n\n**Common issues & fixes:**\n\n• **Forward Head Posture:**\n  - Chin tucks (10 reps, 3x/day)\n  - Face pulls with band\n  - Reduce screen time at eye level\n\n• **Rounded Shoulders:**\n  - Band pull-aparts daily\n  - Chest stretches (30s holds)\n  - Strengthen upper back (rows, face pulls)\n\n• **Anterior Pelvic Tilt (arch in lower back):**\n  - Hip flexor stretches\n  - Strengthen glutes & abs\n  - Posterior pelvic tilt exercises\n\n**Daily habits:**\n• Set a posture reminder every hour\n• Standing desk or monitor at eye level\n• Strengthen your core — it supports everything\n• Walk more — sitting is the enemy of posture\n\nGood posture = less pain, better performance, more confidence! 💪",
    ],
    # Weight training specifics
    "weight_training": [
        "🏋️ Weight Training Fundamentals:\n\n**The Big Lifts (learn these first):**\n• Squat — king of lower body\n• Deadlift — full-body posterior chain\n• Bench Press — chest, shoulders, triceps\n• Overhead Press — shoulders & upper body strength\n• Barbell Row — back thickness\n• Pull-up/Chin-up — back width\n\n**Programming basics:**\n• 3-5 sets per exercise\n• 3-6 reps for strength | 8-12 for hypertrophy | 15+ for endurance\n• 60-90s rest for hypertrophy | 2-5 min for strength\n• Progressive overload every session\n• Train each muscle 2x/week minimum\n\n**Equipment guide:**\n• Barbell — best for compound lifts\n• Dumbbell — great for unilateral work\n• Cables — constant tension, great for isolation\n• Kettlebell — swings, carries, Turkish get-ups\n\nMaster form before adding weight! 🎯",
    ],
    # Body composition
    "body_composition": [
        "📊 Body Composition:\n\n**BMI** (Body Mass Index = weight/height²):\n• Underweight: <18.5\n• Normal: 18.5-24.9\n• Overweight: 25-29.9\n• Obese: 30+\n⚠️ BMI doesn't account for muscle mass — athletes often show 'overweight'\n\n**Better metrics to track:**\n• Body fat % (DEXA scan is most accurate)\n• Waist circumference\n• Progress photos (weekly, same lighting)\n• How clothes fit\n• Strength and energy levels\n\n**Body Recomposition** (lose fat + gain muscle simultaneously):\n• Possible for beginners and those returning after a break\n• Eat at maintenance calories\n• High protein (2g/kg)\n• Strength train 3-4x/week\n• Be patient — it takes longer than either bulking or cutting",
    ],
    # Intermittent Fasting
    "fasting": [
        "⏰ Intermittent Fasting:\n\n**Popular protocols:**\n• 16:8 — fast 16h, eat within 8h window (most popular)\n• 18:6 — slightly more aggressive\n• OMAD — one meal a day (advanced)\n• 5:2 — eat normally 5 days, restrict to 500 kcal 2 days\n\n**Benefits:**\n• Improved insulin sensitivity\n• Calorie restriction made easier for some\n• Cellular autophagy (cellular cleanup)\n• Mental clarity during fasted state\n\n**For muscle building:**\n• Time your training within your eating window\n• Prioritize protein in your meals\n• Not ideal if you struggle to eat enough calories\n\n**Tips:**\n• Black coffee/tea allowed during fast\n• Electrolytes help during longer fasts\n• Don't fast if you have a history of eating disorders\n• Works best when it fits your lifestyle naturally 🙏",
    ],
    # Keto
    "keto": [
        "🥑 Ketogenic Diet:\n\n**What it is:** Very low carb (<50g/day), high fat, moderate protein diet. Forces body to burn fat for fuel (ketosis).\n\n**Macro split:** ~70% fat, 25% protein, 5% carbs\n\n**Best foods:**\n• Fats: avocado, olive oil, nuts, butter, fatty fish\n• Protein: meat, chicken, eggs, cheese\n• Veggies: leafy greens, broccoli, cauliflower, zucchini\n\n**Avoid:** bread, pasta, rice, sugar, most fruits, starchy veg\n\n**Benefits:**\n• Effective for fat loss (reduced hunger)\n• Can improve blood sugar control\n• Mental clarity (once fat-adapted)\n\n**Drawbacks:**\n• Keto flu for first 1-2 weeks (fatigue, headache)\n• Hard to maintain long-term for many\n• Reduced athletic performance initially\n• Not necessary for fat loss — calorie deficit is what matters\n\n💡 Works great for some, not for others. Try it for 4-6 weeks to see how you respond!",
    ],
    # Vegan/Plant-based
    "vegan": [
        "🌱 Plant-Based / Vegan Fitness:\n\n**Getting enough protein (key challenge):**\n• Tofu — 8g per 100g\n• Tempeh — 19g per 100g (best plant protein!)\n• Edamame — 11g per 100g\n• Lentils — 9g per 100g cooked\n• Chickpeas — 8g per 100g cooked\n• Seitan — 25g per 100g (wheat gluten)\n• Pea protein powder — excellent quality\n• Soy protein — complete amino acid profile\n\n**Key nutrients to watch:**\n• B12 — supplement is essential\n• Iron — pair with Vitamin C for absorption\n• Zinc — pumpkin seeds, hemp seeds\n• Omega-3 — algae oil (where fish get it from!)\n• Calcium — fortified plant milks, tofu, leafy greens\n• Vitamin D — supplement especially in winter\n\n**Tips:**\n• Combine protein sources (rice + beans = complete protein)\n• Plant-based athletes perform just as well — it's very doable!\n• Use a food tracker to hit your protein goal daily 💪",
    ],
    # Abs
    "abs": [
        "💪 Building Abs & Core:\n\n**The truth about abs:**\n• Abs are built in the kitchen — diet and low body fat is what reveals them\n• Everyone has abs — they're just hidden under fat\n• ~10-12% body fat for men | ~18-20% for women to see abs\n\n**Best core exercises:**\n• Plank variations — 30-60s holds\n• Ab rollout — extremely effective\n• Hanging leg raises — lower abs\n• Cable crunches — weighted, great for hypertrophy\n• Dead bug — spine-safe and functional\n• Pallof press — anti-rotation strength\n• V-sit — advanced\n\n**Training the core:**\n• Train abs 2-3x/week like any other muscle\n• Use weighted exercises for muscle growth\n• Don't neglect obliques and lower abs\n• Your back and glutes are also core muscles!\n\nFocus on fat loss + compound lifts + dedicated ab work = six-pack! 🎯",
    ],
    # Arms
    "arms": [
        "💪 Arm Training:\n\n**Biceps (curl movements):**\n• Barbell Curl — mass builder\n• Incline Dumbbell Curl — peak contraction\n• Hammer Curl — brachialis (outer arm thickness)\n• Cable Curl — constant tension\n• Concentration Curl — isolation\n\n**Triceps (2/3 of arm size!):**\n• Close-Grip Bench Press — heavy compound\n• Tricep Dips — bodyweight mass builder\n• Skull Crushers — long head emphasis\n• Cable Pushdown — isolation\n• Overhead Tricep Extension — stretches long head\n\n**Training tips:**\n• Biceps are trained on pull days, triceps on push days\n• Add 2-3 direct arm exercises per session\n• 10-15 rep range works well for arms\n• Superset biceps + triceps to save time\n• Rest 60s between sets\n\n💡 Compound lifts (rows, pull-ups, bench, dips) already train arms heavily — isolations are the finisher!",
    ],
    # Chest
    "chest": [
        "🏋️ Chest Training:\n\n**Best chest exercises:**\n• Barbell Bench Press — king of chest mass\n• Incline DB Press — upper chest emphasis\n• Decline Press — lower chest\n• Dumbbell Fly — stretch and isolation\n• Cable Fly / Pec Deck — constant tension\n• Push-ups — bodyweight, great for warmup\n• Dips — lower chest + triceps\n\n**Programming:**\n• 3-4 exercises per chest session\n• Start with compound (bench) then move to isolation\n• Train chest 1-2x per week\n• Use full range of motion — touch chest on bench press\n\n**Common mistakes:**\n• Not going through full ROM\n• Ego lifting with bad form\n• Neglecting upper chest (use incline!)\n• Not retracting scapula on bench — squeeze shoulder blades back\n• Too much pressing, not enough stretching\n\n💡 Feel the stretch at the bottom of every rep for max growth! 🎯",
    ],
    # Back
    "back": [
        "🏋️ Back Training:\n\n**Best back exercises:**\n• Deadlift — full body, massive back builder\n• Pull-ups/Chin-ups — lat width\n• Barbell Rows — upper back thickness\n• Cable Rows — mid-back\n• Lat Pulldowns — lat width (good alternative to pull-ups)\n• Face Pulls — rear delts + upper back health\n• Single-arm DB Row — heavy pulling\n\n**Upper vs. Lower back:**\n• Upper back — rows, face pulls, reverse flies\n• Lats — pull-ups, pulldowns, straight-arm pulldowns\n• Lower back — deadlifts, back extensions, good mornings\n\n**Tips:**\n• Pull with your elbows, not your hands\n• Imagine you're trying to put your shoulder blades in your back pockets\n• Don't neglect your lower back — it's crucial for posture and strength\n• 3-4 back exercises per session, 3-4 sets each\n\n💡 A strong back = better posture, less pain, and a powerful physique! 💪",
    ],
    # Legs
    "legs": [
        "🦵 Leg Training:\n\n**Best leg exercises:**\n• Squat — king of all exercises\n• Romanian Deadlift (RDL) — hamstrings + glutes\n• Leg Press — quad-dominant, safe for beginners\n• Walking Lunges — glutes + functional strength\n• Hip Thrust — glute isolation king\n• Leg Curl — hamstring isolation\n• Leg Extension — quad isolation\n• Calf Raises — gastrocnemius + soleus\n\n**Programming:**\n• Squat early in session (most demanding)\n• 4-6 exercises per leg session\n• 8-12 reps for hypertrophy, 3-6 for strength\n• Train legs 2x/week for optimal growth\n\n**Don't skip leg day because:**\n• Legs are 60% of your body's muscle mass\n• Leg training releases the most testosterone and growth hormone\n• Strong legs = better athletic performance\n• Imbalanced physique looks bad!\n\n💡 If squats hurt your knees — check your form, depth, and foot position! 🎯",
    ],
    # Shoulders
    "shoulders": [
        "💪 Shoulder Training:\n\n**Best shoulder exercises:**\n• Overhead Press (OHP) — mass builder (barbell or dumbbell)\n• Lateral Raises — side delt width (the 3D look!)\n• Face Pulls — rear delt health + posture\n• Front Raises — anterior delt\n• Rear Delt Fly — posterior delt\n• Arnold Press — all 3 heads\n• Upright Row — traps + side delts\n\n**The 3 Deltoid Heads:**\n• Front (Anterior) — trained heavily by bench press\n• Side (Lateral) — lateral raises for width\n• Rear (Posterior) — most neglected! Face pulls & flies\n\n**Shoulder health tips:**\n• Warm up rotator cuff before pressing\n• Face pulls should be in EVERY training session\n• Strengthen external rotators to prevent impingement\n• Balance pressing with pulling volume\n\n💡 Capped shoulders are built with lateral raises — do them every session! 🎯",
    ],
    # Nutrition timing
    "nutrition_timing": [
        "⏰ Nutrition Timing:\n\n**Pre-workout meal (1-2h before):**\n• Complex carbs + lean protein\n• Example: oats + protein shake | rice + chicken | banana + peanut butter\n• Avoid heavy fats right before training (slows digestion)\n• Stay hydrated\n\n**Post-workout meal (within 1-2h):**\n• Protein + fast carbs for recovery\n• Example: protein shake + banana | chicken + rice | Greek yogurt + fruit\n• This is when muscles are most receptive to nutrients\n\n**Overall truth:**\n• Nutrient timing matters much LESS than total daily intake\n• Total protein, calories, and sleep are 10x more important than meal timing\n• If you hit your daily targets, timing is just optimization\n\n**For muscle gain:** Eat something with protein every 3-4 hours\n**For fat loss:** Eat when it fits your schedule and keeps you full\n\n💡 Meal timing is a 5% factor. Nail the basics first! 🎯",
    ],
    # Plateau
    "weight_plateau": [
        "📉 Breaking a Weight Plateau:\n\n**Why plateaus happen:**\n• Body adapts to calorie deficit — metabolism slows\n• Less body weight = fewer calories burned\n• Muscle loss reduces metabolic rate\n\n**How to break it:**\n\n1. **Recalculate your TDEE** — you now weigh less, need fewer calories\n2. **Diet break** — 1-2 weeks at maintenance, then resume deficit\n3. **Increase NEAT** — walk more, take stairs, be more active\n4. **Change your training** — new exercises, higher volume\n5. **Check your tracking** — are you actually in a deficit? Measure and weigh food\n6. **Reduce liquid calories** — they add up fast\n7. **Refeed day** — one day at maintenance calories per week\n\n**Don't:**\n• Slash calories drastically\n• Do excessive cardio\n• Give up — plateaus are normal and temporary!\n\n💡 If you've been in a deficit for 12+ weeks, take a 2-week break at maintenance. You'll come back stronger! 💪",
    ],
    # Hormones
    "hormones": [
        "🧬 Hormones & Fitness:\n\n**Testosterone (muscle building, fat loss):**\n• Boost naturally: heavy compound lifts, sleep 8h, reduce stress, eat healthy fats, get sunlight\n• Avoid: chronic cardio, excessive alcohol, chronic sleep deprivation, crash dieting\n\n**Cortisol (stress hormone):**\n• High cortisol = fat retention + muscle breakdown\n• Reduce: sleep more, meditate, limit caffeine, avoid overtraining, eat enough\n\n**Insulin (nutrient storage):**\n• Exercise improves insulin sensitivity — your cells use carbs more efficiently\n• High carb diets + sedentary lifestyle = insulin resistance\n• Strength training is the best insulin sensitizer\n\n**Growth Hormone:**\n• Released during sleep (mostly in deep sleep)\n• Boosted by fasting, HIIT, compound lifts\n• Reason sleep is so critical for muscle growth\n\n💡 Optimizing hormones naturally through sleep, training, and diet beats any supplement stack! 🔬",
    ],
    # Aging
    "aging": [
        "👴 Fitness After 40+:\n\n**What changes with age:**\n• Natural testosterone decline (~1% per year after 30)\n• Slower recovery — need more rest days\n• Loss of muscle mass (sarcopenia) if inactive\n• Joints need more care and warmup time\n• Metabolism slows gradually\n\n**What to do:**\n• Strength train — it's THE most important activity for aging well\n• Prioritize protein (2g/kg) — harder to build/maintain muscle with age\n• Sleep 8+ hours — recovery is longer\n• More warmup time before sessions\n• Include mobility work daily\n• Reduce injury risk — ego lifting is not worth it\n\n**The good news:**\n• You can absolutely build muscle and get fit at any age\n• Many people are in the best shape of their lives in their 40s and 50s\n• Consistency over decades beats intensity in youth\n\n💡 \"You don't stop moving because you get old. You get old because you stop moving!\" 💪",
    ],
    # Women's fitness
    "women": [
        "👩 Women's Fitness Guide:\n\n**Myths to bust:**\n• Lifting heavy will NOT make you bulky — women have 10-15x less testosterone than men\n• Cardio alone is NOT the best approach for body composition\n• Fat loss happens through calorie deficit, not spot reduction\n\n**Training:**\n• Strength train 3-4x per week — best for body recomposition\n• Higher rep ranges (10-15) tend to work well hormonally\n• Include hip thrusts, Romanian deadlifts, squats for glutes\n• Cardio is supplementary, not the main event\n\n**Nutrition:**\n• Iron — higher needs due to menstruation (lean meats, spinach, lentils)\n• Calcium + Vitamin D — bone health is critical\n• Protein: 1.6-2g/kg just like men\n• Don't undereat — fueling your body is essential\n\n**Hormonal considerations:**\n• Performance naturally varies with menstrual cycle\n• Follicular phase (post-period): peak strength and energy\n• Luteal phase: may feel more fatigued — reduce intensity if needed\n\n💡 Women respond incredibly well to strength training. Lift heavy, eat well, get strong! 💪",
    ],
    # Home workout
    "home_workout": [
        "🏠 Home Workout Guide:\n\n**No equipment needed:**\n• Push-ups (chest, shoulders, triceps)\n• Pull-ups (if you have a bar) or door rows\n• Squats and lunges (quads, glutes)\n• Hip thrusts (glutes)\n• Pike push-ups (shoulders)\n• Dips on a chair (triceps)\n• Plank variations (core)\n• Burpees (full body cardio)\n\n**Home workout programs:**\n• 3x Full Body: Squat 3x15 | Push-up 3x15 | Hip Thrust 3x15 | Plank 3x45s\n• Upper/Lower Split if you have dumbbells\n\n**Make it harder:**\n• Add weight (backpack, water bottles)\n• Increase reps or sets\n• Slow down the movement (3s down, 1s up)\n• Reduce rest time\n• Add plyometrics (jump squats, clap push-ups)\n\n**Equipment worth getting:**\n• Pull-up bar (~$20) — game changer\n• Resistance bands (~$15) — very versatile\n• Adjustable dumbbells — if budget allows\n\n💡 You can build an impressive physique with zero gym equipment! Consistency > equipment 🎯",
    ],
    # Gym tips
    "gym_tips": [
        "🏋️ Gym Tips for Success:\n\n**First time at the gym:**\n• Go during off-peak hours (early morning or midday)\n• Follow a structured program — don't wing it\n• Ask staff for equipment orientation\n• Start light, focus on form\n• Don't hog multiple machines\n\n**Gym etiquette:**\n• Re-rack your weights after every set\n• Wipe down equipment after use\n• Don't give unsolicited advice\n• Limit rest on busy machines to 90s\n• Headphones on = don't disturb me 😄\n\n**Make the most of your session:**\n• Have a plan before you arrive\n• Track what you lift\n• Arrive 5 min early to warm up\n• Focus on the muscle you're training\n• Leave ego at the door\n\n**Programs for beginners:**\n• StrongLifts 5x5 — simple barbell program\n• GZCLP — flexible and effective\n• Reddit PPL — popular push/pull/legs\n• Starting Strength — classic beginner barbell program\n\n💡 The best gym is the one you actually go to. Just show up! 💪",
    ],
}


KEYWORD_MAP = {
    "greeting": ["hi", "hello", "hey", "sup", "yo", "hola", "greetings", "howdy", "good morning", "good evening", "what's up", "wassup", "good afternoon"],
    "weight_loss": ["lose weight", "fat loss", "weight loss", "burn fat", "cut", "cutting", "slim", "lean", "shred", "lose fat", "get lean", "get thin", "belly fat", "lose belly", "tummy fat", "drop weight", "reduce weight"],
    "muscle_gain": ["build muscle", "muscle gain", "bulk", "bulking", "mass", "grow muscle", "get big", "hypertrophy", "get jacked", "get strong", "strength", "muscle", "gain mass", "put on muscle", "bigger muscles"],
    "diet": ["diet", "nutrition", "eat", "food", "meal", "calories", "protein", "carbs", "macros", "healthy eating", "what to eat", "meal plan", "clean eating", "healthy food", "junk food", "processed food", "whole food"],
    "workout": ["workout", "exercise", "training", "gym", "lift", "lifting", "routine", "program", "chest", "back", "legs", "arms", "shoulders", "abs", "core", "glutes", "hamstring", "quadricep", "bicep", "tricep", "lat", "trap"],
    "supplements": ["supplement", "creatine", "whey", "protein powder", "vitamins", "pre workout", "bcaa", "omega", "collagen", "casein", "glutamine", "beta alanine", "citrulline", "preworkout"],
    "sleep": ["sleep", "insomnia", "rest quality", "sleeping", "tired", "fatigue", "nap", "sleep schedule", "cant sleep", "wake up", "oversleeping", "melatonin", "sleep deprivation"],
    "motivation": ["motivat", "inspire", "quote", "discipline", "give up", "can't", "hard", "struggling", "lazy", "unmotivated", "no energy", "procrastinat", "self control", "willpower", "consistency", "habit"],
    "stretching": ["stretch", "flexibility", "mobility", "warm up", "cool down", "yoga", "foam roll", "tight muscle", "stiff", "range of motion", "dynamic stretch", "static stretch", "hip flexor"],
    "beginner": ["beginner", "start", "new to", "first time", "never worked out", "newbie", "starting out", "where to begin", "how to start", "just started"],
    "rest": ["rest day", "recovery", "overtrain", "sore", "doms", "rest days", "day off", "muscle soreness", "delayed onset", "overtraining", "active recovery"],
    "cardio": ["cardio", "running", "jogging", "hiit", "cycling", "swimming", "aerobic", "endurance", "stamina", "treadmill", "elliptical", "stair", "zone 2", "vo2 max", "heart rate"],
    "hydration": ["water", "hydrat", "drink", "thirst", "dehydrat", "electrolyte", "sports drink", "coconut water"],
    "injury": ["injury", "pain", "hurt", "sore knee", "back pain", "shoulder pain", "sprain", "strain", "tendon", "ligament", "recover from injury", "knee pain", "wrist pain", "ankle", "shin splint", "pulled muscle"],
    "mental_health": ["mental health", "stress", "anxiety", "depression", "mood", "mental", "burnout", "overwhelm", "emotional", "mindset", "mindfulness", "meditation", "breathe", "calm", "peace"],
    "yoga": ["yoga", "pilates", "namaste", "asana", "vinyasa", "downward dog", "warrior pose", "sun salutation", "yin yoga", "hot yoga", "hatha"],
    "posture": ["posture", "slouch", "hunchback", "forward head", "rounded shoulders", "spine", "sit straight", "desk posture", "ergonomic", "alignment"],
    "weight_training": ["barbell", "dumbbell", "kettlebell", "squat", "deadlift", "bench press", "overhead press", "row", "pull up", "chin up", "lunge", "rdl", "romanian", "sumo", "powerlifting", "weightlifting", "olympic lift"],
    "body_composition": ["body fat", "bmi", "body composition", "lean mass", "fat percentage", "muscle mass", "visceral fat", "body recomposition", "recomp", "body measurement"],
    "fasting": ["fast", "fasting", "intermittent fast", "16:8", "omad", "one meal a day", "eat window", "skip breakfast", "keto"],
    "keto": ["keto", "ketogenic", "ketosis", "low carb", "no carb", "fat adapted", "atkins", "carnivore"],
    "vegan": ["vegan", "vegetarian", "plant based", "no meat", "tofu", "tempeh", "lentil", "plant protein", "dairy free"],
    "abs": ["abs", "six pack", "core workout", "ab workout", "crunches", "plank", "v-sit", "leg raise", "oblique", "stomach", "midsection", "flat stomach"],
    "arms": ["bicep", "tricep", "arm workout", "curl", "arm day", "bigger arms", "tone arms", "forearm"],
    "chest": ["chest workout", "chest exercise", "push up", "bench", "pec", "chest press", "fly", "cable fly", "dip"],
    "back": ["back workout", "pull day", "lat", "row", "pull up", "deadlift", "back exercise", "lower back", "upper back", "rhomboid"],
    "legs": ["leg workout", "leg day", "squat", "lunge", "leg press", "hamstring", "quad", "calf", "glute", "hip thrust", "leg curl", "leg extension"],
    "shoulders": ["shoulder workout", "shoulder exercise", "deltoid", "overhead press", "lateral raise", "front raise", "rear delt", "shoulder press", "rotator cuff"],
    "nutrition_timing": ["meal timing", "pre workout meal", "post workout meal", "when to eat", "eat before", "eat after", "nutrient timing", "carb timing"],
    "weight_plateau": ["plateau", "stuck", "not losing weight", "weight stopped", "no progress", "hit a wall", "same weight", "stalled"],
    "hormones": ["testosterone", "cortisol", "insulin", "estrogen", "hormone", "growth hormone", "thyroid", "leptin", "ghrelin"],
    "aging": ["aging", "over 40", "over 50", "older", "senior fitness", "age", "40s", "50s", "60s", "menopause", "elder"],
    "women": ["women", "female", "girl", "lady", "feminine", "pregnancy", "postpartum", "period", "menstrual", "hormonal"],
    "kids": ["kids", "children", "teenage", "teen", "youth", "young", "child fitness", "junior"],
    "home_workout": ["home workout", "no gym", "no equipment", "bodyweight", "calisthenics", "workout at home", "apartment", "small space"],
    "gym_tips": ["gym tips", "gym etiquette", "first gym", "gym advice", "gym routine", "which gym", "gym membership", "equipment"],
}


def smart_reply(message: str) -> str:
    msg = message.lower().strip()
    
    # Check each category
    best_match = None
    best_score = 0
    
    for category, keywords in KEYWORD_MAP.items():
        for keyword in keywords:
            if keyword in msg:
                score = len(keyword)  # longer keyword = more specific match
                if score > best_score:
                    best_score = score
                    best_match = category
    
    if best_match:
        return random.choice(RESPONSES[best_match])
    
    return random.choice(RESPONSES["default"])


# ---- Daily Tips ----
DAILY_TIPS = [
    {"tip": "Drink a full glass of water first thing in the morning. It kickstarts your metabolism and helps your body wake up.", "emoji": "💧"},
    {"tip": "Progressive overload is the key to growth. Add one more rep, one more set, or a little more weight each session.", "emoji": "📈"},
    {"tip": "Sleep is when your muscles actually grow. Prioritize 7-9 hours of quality sleep every night.", "emoji": "😴"},
    {"tip": "Don't skip the warm-up! 5-10 minutes of dynamic stretching reduces injury risk dramatically.", "emoji": "🧘"},
    {"tip": "Protein timing matters less than total daily intake. Focus on hitting your daily target consistently.", "emoji": "🥩"},
    {"tip": "Walking is the most underrated exercise. 10,000 steps a day can transform your health and body composition.", "emoji": "🚶"},
    {"tip": "Consistency beats intensity. A moderate workout done 5x/week beats an intense one done once a week.", "emoji": "🔥"},
    {"tip": "Your body adapts to stress. Change your routine every 4-6 weeks to keep making progress.", "emoji": "🔄"},
    {"tip": "Creatine monohydrate is the most researched and effective supplement. 5g per day, every day.", "emoji": "💊"},
    {"tip": "Rest days are growth days. Your muscles repair and get stronger during recovery, not during the workout.", "emoji": "🌙"},
    {"tip": "Track your workouts. If you're not measuring, you're not managing. A simple log makes a huge difference.", "emoji": "📝"},
    {"tip": "Eat the rainbow! Different colored vegetables provide different micronutrients your body needs.", "emoji": "🥦"},
]


# ---- Routes ----

@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")


@app.post("/api/chat")
async def chat(request: ChatRequest):
    reply = smart_reply(request.message)
    return {"reply": reply}


@app.post("/api/plan")
async def generate_plan(request: PlanRequest):
    user_data["age"] = request.age
    user_data["weight"] = request.weight
    user_data["height"] = request.height

    bmi = calc_bmi(request.weight, request.height)
    bf = body_fat_estimate(request.weight, request.height, request.age)
    adjustment = adjust_plan(progress_history)
    exp = request.experience

    if request.goal == "muscle gain":
        if exp == "beginner":
            workout = """WORKOUT (Full Body 3x/week):
- Squat 3x10
- Bench Press 3x10
- Bent-over Row 3x10
- Overhead Press 3x10
- Deadlift 2x8
- Pull-ups 3x AMRAP
- Plank 3x30s

DIET:
- Calories: TDEE + 400 kcal surplus
- Protein: 1.8g per kg bodyweight
- Focus on whole foods, complex carbs, lean protein
- Eat 4-5 meals spread throughout the day

TIPS:
- Focus on learning proper form first
- Progressive overload: add weight when you hit all reps
- Rest 90-120 seconds between sets
- Track every workout in a log"""
        elif exp == "intermediate":
            workout = """WORKOUT (Upper/Lower Split 4x/week):
Day 1 — Upper:
- Bench Press 4x8
- Barbell Row 4x8
- OHP 3x10
- Pull-ups 3x10
- Dumbbell Curls 3x12
- Tricep Pushdowns 3x12

Day 2 — Lower:
- Squat 4x8
- Romanian Deadlift 3x10
- Leg Press 3x12
- Leg Curls 3x12
- Calf Raises 4x15
- Ab Rollouts 3x10

DIET:
- Calories: TDEE + 350 kcal surplus
- Protein: 2.0g per kg bodyweight
- Carb-cycle: higher carbs on training days

TIPS:
- Train each muscle 2x per week for optimal growth
- Deload every 4-5 weeks
- Sleep 8+ hours for maximum recovery"""
        else:
            workout = """WORKOUT (Push/Pull/Legs 6x/week):
Day 1 — Push:
- Bench Press 4x6
- Incline DB Press 4x10
- OHP 3x8
- Cable Flyes 3x12
- Lateral Raises 4x15
- Tricep Dips 3x12

Day 2 — Pull:
- Deadlift 3x5
- Weighted Pull-ups 4x8
- Barbell Rows 4x8
- Face Pulls 3x15
- Barbell Curls 3x10
- Hammer Curls 3x12

Day 3 — Legs:
- Squat 4x6
- Front Squat 3x8
- RDL 3x10
- Leg Press 4x12
- Walking Lunges 3x12
- Calf Raises 5x15

DIET:
- Calories: TDEE + 300 kcal lean bulk
- Protein: 2.2g per kg bodyweight
- Periodize nutrition with training phases

TIPS:
- Use RPE 8-9 for main lifts
- Include both strength (3-6 rep) and hypertrophy (8-12) ranges
- Prioritize sleep and stress management"""

    else:  # fat loss
        if exp == "beginner":
            workout = """WORKOUT (Full Body 3x/week + Cardio):
- Goblet Squat 3x12
- Push-ups 3x AMRAP
- Dumbbell Rows 3x12 each
- Lunges 3x10 each
- Plank 3x30s

CARDIO:
- Walk 30 min daily (aim for 8,000 steps)
- 2x HIIT sessions (15-20 min)

DIET:
- Calories: TDEE - 500 kcal deficit
- Protein: 2.0g per kg bodyweight (to preserve muscle)
- Fill half your plate with vegetables
- Reduce liquid calories and processed snacks

TIPS:
- Don't crash diet — slow and steady wins
- Weigh yourself weekly, same time, same conditions
- Focus on building healthy habits, not just losing weight"""
        elif exp == "intermediate":
            workout = """WORKOUT (Upper/Lower 4x/week + Cardio):
Day 1 — Upper:
- Bench Press 4x10
- Cable Rows 4x10
- DB Shoulder Press 3x12
- Lat Pulldowns 3x12
- Superset: Curls + Tricep Extensions 3x15

Day 2 — Lower:
- Squat 4x10
- RDL 3x12
- Leg Press 3x15
- Walking Lunges 3x12
- Ab Circuit: 3 rounds

CARDIO:
- 3x HIIT (20 min): sprints, bike intervals, rowing
- Daily walking: 10,000 steps target

DIET:
- Calories: TDEE - 500 kcal deficit
- Protein: 2.0g per kg
- High volume, low calorie foods (vegetables, lean meats)
- Track macros for accuracy

TIPS:
- Strength train to preserve muscle during a cut
- Refeed days every 10-14 days (eat at maintenance)
- Manage stress — cortisol increases fat storage"""
        else:
            workout = """WORKOUT (PPL 5-6x/week + Strategic Cardio):
Push/Pull/Legs rotation with higher volume and supersets.
- Keep main compound lifts heavy (6-8 reps)
- Use supersets and drop sets for accessories
- Include 2 ab sessions per week

CARDIO:
- 2x HIIT (25 min)
- 3x LISS (fasted walking 30-45 min)
- Zone 2 cardio for fat oxidation

DIET:
- Calories: TDEE - 450 kcal (aggressive but sustainable)
- Protein: 2.4g per kg (higher during cut to preserve muscle)
- Carb cycling: low carb on rest days, moderate on training days
- Strategic refeeds every 7-10 days

TIPS:
- Monitor performance — if lifts drop significantly, eat more
- Use diet breaks (1-2 weeks at maintenance) every 6-8 weeks
- Prioritize sleep and recovery even more during a cut"""

    plan = f"""Age: {request.age} | BMI: {bmi} | Est Body Fat: {bf}%
Goal: {request.goal.title()} | Level: {exp.title()}

{workout}

{adjustment}"""

    return {"plan": plan}


@app.get("/api/analysis")
async def weekly_analysis():
    if len(progress_history) < 2:
        return {"analysis": "Not enough data"}
    start = progress_history[0]["weight"]
    end = progress_history[-1]["weight"]
    change = round(end - start, 1)
    msg = "Losing weight 🎉" if change < 0 else "Gaining weight 💪"
    return {
        "start_weight": start,
        "end_weight": end,
        "change": change,
        "message": msg
    }


@app.get("/api/tips")
async def daily_tip():
    tip = random.choice(DAILY_TIPS)
    return tip


DB_PATH = "fitbot.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS workout_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 0,
        exercise TEXT NOT NULL,
        sets INTEGER,
        reps INTEGER,
        weight REAL,
        notes TEXT,
        logged_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS water_intake (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 0,
        glasses INTEGER DEFAULT 1,
        logged_date TEXT DEFAULT (date('now','localtime'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS progress_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER DEFAULT 0,
        weight REAL,
        body_fat REAL,
        notes TEXT,
        logged_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        role TEXT DEFAULT 'client',
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL
    )""")
    conn.commit()
    # Seed default admin account
    existing = conn.execute("SELECT id FROM users WHERE username='admin'").fetchone()
    if not existing:
        salt = secrets.token_hex(16)
        pw_hash = hashlib.sha256(("admin123" + salt).encode()).hexdigest()
        conn.execute(
            "INSERT INTO users (username, email, password_hash, salt, role) VALUES (?,?,?,?,?)",
            ("admin", "admin@fitbot.ai", pw_hash, salt, "admin")
        )
        conn.commit()
    conn.close()

init_db()


# ---- Auth Helpers ----
def hash_password(password: str, salt: str) -> str:
    return hashlib.sha256((password + salt).encode()).hexdigest()

def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    expires = (datetime.now() + timedelta(days=7)).isoformat()
    conn = get_db()
    conn.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?,?,?)", (token, user_id, expires))
    conn.commit()
    conn.close()
    return token

def get_user_from_token(request: Request):
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth[7:]
    conn = get_db()
    row = conn.execute(
        "SELECT u.id, u.username, u.email, u.role FROM sessions s JOIN users u ON s.user_id=u.id WHERE s.token=? AND s.expires_at > datetime('now','localtime')",
        (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---- Auth Models ----
class SignupRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str


# ---- Auth Endpoints ----
@app.post("/api/auth/signup")
async def signup(req: SignupRequest):
    if len(req.username) < 3:
        return JSONResponse({"error": "Username must be at least 3 characters"}, 400)
    if len(req.password) < 6:
        return JSONResponse({"error": "Password must be at least 6 characters"}, 400)
    conn = get_db()
    existing = conn.execute("SELECT id FROM users WHERE username=? OR email=?", (req.username, req.email)).fetchone()
    if existing:
        conn.close()
        return JSONResponse({"error": "Username or email already exists"}, 409)
    # First user after admin seed becomes admin too if desired; else client
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    role = "admin" if user_count == 0 else "client"
    salt = secrets.token_hex(16)
    pw_hash = hash_password(req.password, salt)
    conn.execute(
        "INSERT INTO users (username, email, password_hash, salt, role) VALUES (?,?,?,?,?)",
        (req.username, req.email, pw_hash, salt, role)
    )
    conn.commit()
    user_id = conn.execute("SELECT id FROM users WHERE username=?", (req.username,)).fetchone()[0]
    conn.close()
    token = create_session(user_id)
    return {"token": token, "username": req.username, "role": role}

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE username=?", (req.username,)).fetchone()
    conn.close()
    if not user:
        return JSONResponse({"error": "Invalid username or password"}, 401)
    pw_hash = hash_password(req.password, user["salt"])
    if pw_hash != user["password_hash"]:
        return JSONResponse({"error": "Invalid username or password"}, 401)
    token = create_session(user["id"])
    return {"token": token, "username": user["username"], "role": user["role"]}

@app.post("/api/auth/logout")
async def logout(request: Request):
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        conn = get_db()
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
        conn.close()
    return {"status": "ok"}

@app.get("/api/auth/me")
async def get_me(request: Request):
    user = get_user_from_token(request)
    if not user:
        return JSONResponse({"error": "Not authenticated"}, 401)
    return user


# ---- Admin Endpoints ----
@app.get("/api/admin/users")
async def admin_get_users(request: Request):
    user = get_user_from_token(request)
    if not user or user["role"] != "admin":
        return JSONResponse({"error": "Forbidden"}, 403)
    conn = get_db()
    rows = conn.execute("SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC").fetchall()
    conn.close()
    return {"users": [dict(r) for r in rows]}

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: int, request: Request):
    user = get_user_from_token(request)
    if not user or user["role"] != "admin":
        return JSONResponse({"error": "Forbidden"}, 403)
    if user_id == user["id"]:
        return JSONResponse({"error": "Cannot delete yourself"}, 400)
    conn = get_db()
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/admin/stats")
async def admin_stats(request: Request):
    user = get_user_from_token(request)
    if not user or user["role"] != "admin":
        return JSONResponse({"error": "Forbidden"}, 403)
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    logs = conn.execute("SELECT COUNT(*) FROM workout_logs").fetchone()[0]
    water = conn.execute("SELECT SUM(glasses) FROM water_intake").fetchone()[0] or 0
    progress = conn.execute("SELECT COUNT(*) FROM progress_log").fetchone()[0]
    conn.close()
    return {"total_users": users, "total_workout_logs": logs, "total_water_glasses": water, "total_progress_entries": progress}

@app.patch("/api/admin/users/{user_id}/role")
async def admin_change_role(user_id: int, request: Request):
    user = get_user_from_token(request)
    if not user or user["role"] != "admin":
        return JSONResponse({"error": "Forbidden"}, 403)
    body = await request.json()
    new_role = body.get("role", "client")
    if new_role not in ("admin", "client"):
        return JSONResponse({"error": "Invalid role"}, 400)
    conn = get_db()
    conn.execute("UPDATE users SET role=? WHERE id=?", (new_role, user_id))
    conn.commit()
    conn.close()
    return {"status": "ok"}


# ---- DB Routes (user-scoped) ----
@app.post("/api/workout-log")
async def log_workout(entry: WorkoutEntry, request: Request):
    user = get_user_from_token(request)
    user_id = user["id"] if user else 0
    conn = get_db()
    conn.execute(
        "INSERT INTO workout_logs (user_id, exercise, sets, reps, weight, notes) VALUES (?,?,?,?,?,?)",
        (user_id, entry.exercise, entry.sets, entry.reps, entry.weight, entry.notes)
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Workout logged!"}

@app.get("/api/workout-log")
async def get_workout_logs(days: int = 7, request: Request = None):
    user = get_user_from_token(request) if request else None
    user_id = user["id"] if user else 0
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM workout_logs WHERE user_id=? AND logged_at >= datetime('now', ?, 'localtime') ORDER BY logged_at DESC",
        (user_id, f"-{days} days")
    ).fetchall()
    conn.close()
    return {"logs": [dict(r) for r in rows]}

@app.post("/api/water")
async def log_water(entry: WaterEntry, request: Request):
    user = get_user_from_token(request)
    user_id = user["id"] if user else 0
    today = date.today().isoformat()
    conn = get_db()
    row = conn.execute("SELECT id, glasses FROM water_intake WHERE user_id=? AND logged_date=?", (user_id, today)).fetchone()
    if row:
        conn.execute("UPDATE water_intake SET glasses=? WHERE id=?", (row["glasses"] + entry.glasses, row["id"]))
    else:
        conn.execute("INSERT INTO water_intake (user_id, glasses, logged_date) VALUES (?,?,?)", (user_id, entry.glasses, today))
    conn.commit()
    conn.close()
    return {"status": "ok"}

@app.get("/api/water")
async def get_water(request: Request):
    user = get_user_from_token(request)
    user_id = user["id"] if user else 0
    today = date.today().isoformat()
    conn = get_db()
    row = conn.execute("SELECT glasses FROM water_intake WHERE user_id=? AND logged_date=?", (user_id, today)).fetchone()
    conn.close()
    return {"glasses": row["glasses"] if row else 0, "date": today}

@app.post("/api/progress")
async def log_progress(entry: ProgressEntry, request: Request):
    user = get_user_from_token(request)
    user_id = user["id"] if user else 0
    conn = get_db()
    conn.execute(
        "INSERT INTO progress_log (user_id, weight, body_fat, notes) VALUES (?,?,?,?)",
        (user_id, entry.weight, entry.body_fat, entry.notes)
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Progress logged!"}

@app.get("/api/progress")
async def get_progress(request: Request):
    user = get_user_from_token(request)
    user_id = user["id"] if user else 0
    conn = get_db()
    rows = conn.execute("SELECT * FROM progress_log WHERE user_id=? ORDER BY logged_at DESC LIMIT 30", (user_id,)).fetchall()
    conn.close()
    return {"history": [dict(r) for r in rows]}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = "0.0.0.0" if os.environ.get("PORT") else "127.0.0.1"
    print("\n🤖 FitBot AI Server starting...")
    print(f"🌐 Open http://127.0.0.1:{port} in your browser\n")
    uvicorn.run(app, host=host, port=port)

