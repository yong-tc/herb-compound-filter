# TCM-SM-MS Streamlit App Setup
mkdir -p ~/.streamlit
cat > ~/.streamlit/config.toml <<EOF
[server]
headless = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
server端的Type = "never"
EOF

# Install dependencies
pip install -r requirements.txt -q

# Run the app
streamlit run tcm_identifier.py
