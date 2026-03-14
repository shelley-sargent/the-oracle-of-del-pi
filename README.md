# Weather & Moon Phase Dashboard

I wanted to create a daily dashboard that displays the weather and moon phase in an easy-to-access format for daily reference. After finding an old Nook quite literally in my closet, I decided to get it up and running again and root it. I then used Python to develop a script that runs daily via cron and pushes a PNG displaying the desired information (in a visually appealing manner) to the Nook's browser using nginx on my local server.

The information is assembled via the `python-weather` and `moon` libraries, alongside a manually compiled CSV of quotes and a small image. The PNG is created using Pillow, and displayed on Lightning Browser through the ReLaunch OS on an old Nook Glowlight BNRV510.

[![daily.png](https://i.postimg.cc/5268BrpW/daily.png)](https://postimg.cc/5XWH1nZs)

*Daily dashboard displayed on e-ink screen*

## How It Works

1. **Data Collection** - Python script fetches current weather and calculates moon phase
2. **Quote Selection** - Random quote pulled from curated CSV
3. **Image Generation** - Pillow creates optimized PNG for e-ink display
4. **Deployment** - Image pushed to nginx server on local network
5. **Display** - Nook's Lightning Browser loads the dashboard page

## Hardware

**Nook Glowlight BNRV510** (self-refurbished)
- Replaced battery
- Reconnected touch screen ribbon cable
- Rooted and configured for custom applications
- E-ink display for low power consumption and excellent readability

## Roadmap

- [ ] Display PNG on browser page that automatically refreshes
- [ ] Enable always-on display on the Nook
- [ ] Optimize Nook battery life for extended uptime

## Skills Demonstrated

- **Python scripting** - Data fetching and daily automation
- **Image manipulation** - Pillow/PIL for e-ink optimization
- **Web server configuration** - nginx deployment and hosting
- **Hardware modification** - E-reader refurbishment and rooting
- **Task automation** - Cron job scheduling
- **Network configuration** - Local server setup

## Technical Stack

- Python 3.x
- `python-weather` - Weather data retrieval
- `moon` - Lunar phase calculations
- Pillow (PIL) - Image generation
- nginx - Web server
- Cron - Scheduled tasks
- Lightning Browser - Lightweight Android browser
- ReLaunch - Custom launcher for rooted Nook
