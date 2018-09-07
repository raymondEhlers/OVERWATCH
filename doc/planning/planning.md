---
title: "Trending and alarms in Overwatch"
author:
- Raymond Ehlers\inst{1} for the ALICE Collaboration
shortAuthor: Raymond Ehlers (Yale)
institute: |
 \inst{1}Relativistic Heavy Ion Group \ \
 Department of Physics, Yale University

date: 9 July 2018
graphics: true
header-includes:
- \usepackage{amssymb}
- \usepackage{amsmath}
- \usepackage{siunitx}
- \usepackage{tikz}
- \usetikzlibrary{shapes,arrows}
- \usetikzlibrary{fit,calc}
- \usepackage{marvosym} # For \MVRightArrow{}
- \input{$HOME/.pandoc/preamble/beamer.tex}
- \definecolor{YaleDarkBlue}{RGB}{0,62,114}
- \setbeamercolor{normal text}{fg=YaleDarkBlue, bg=black!2} # I don't think we have to specify the bg color, but it's done for safety. (It's black!2)
- \setbeamertemplate{frame footer}{\insertshortauthor~-~\insertdate}
theme: metropolis
# Invoke with: pandoc --standalone -t beamer pandocPresentation.md -o pandocPresentation.pdf
---

# Tasks

- `[ ]` Define trending API
- `[ ]` Overwatch trending wrapper 
    - First iteration completed
    - Needs an update to better store the trended values
- `[ ]` Define alarm API
- `[ ]` Overwatch alarms wrapper
    - Overwatch stores in histogram information.
        - Better to store in metadata database? (Written out to YAML too?)
- `[ ]` Load functions from c++
    - How to handle possible naming conflicts?
- `[ ]` Implement trending tasks in c++
    - Update Overwatch wrapper with changes
- `[ ]` Implement alarms in c++

# O2 devices

- O2 devices needs to specify:
    - Input sources
    - Output sources
    - Functionality
- All of this needs to eventually be in c++ (or at least easily ported).
    - What parts will Overwatch handle, what will components handle?

![](images/o2DeviceArch.png)

# General trending information

![](images/o2FrameworkConfig.png)


# Trending API/1

[DQM trending manual as reference](https://alice-daq.web.cern.ch/products/amore-modules-developer-manual-part-2#Trending)

- Initialization step where we specify input, output, and construct any necessary objects.
    - Required information?
        - List of histograms available? More abstract?
        - Also subsystems?
        - What else?
    - `std::vector<std::string> init(std::vector<std::string> hists)` returns the request ROT objects?

# Trending API/2

- Some sort of main processing functionality.
    - Required information?
        - Histograms (potentially a vector of them)?
        - Run state information?
    - `template <typename T> T process(std::vector <TH1*> hists, MonitorObject & runState)` which returns the
      trended value(s)?

# Trending API/3

- Some sort of presentation functionality?
    - Required information?
        - Trending hist to style?
        - Canvas to apply additional styles?
        - Can we store the styling more generically so the canvas doesn't need to be available?
    - `void presentOutput(TH1 * hist, TCanvas * canvas)`?
        - This approximately matches what is done currently for Overwatch.
    - Better Delegate entirely to JSRoot / later stages?
        - Is this sufficient?

# Trending API/4

- Some sort of cleanup step
    - `void cleanup()`
- Anything else?

# Alarms

- Overwatch stores alarm like information in the `processingClasses.histogramConatiner.information` dict.
    - Associated with a histogram, which is convenient for single histograms, but not so much for general
      access of such information
- Some sort of alarm function?
    - `template <typename T> bool triggerAlarm(std::string alarmName, T value)`?
    - `bool isAlarmTriggered(std::string alarmName, T value)`
    - Better way to define alarm names?

<!--

# Architecture

\begin{center}
\begin{tikzpicture}[node distance = 1cm, auto]
	\tikzstyle{block} = [rectangle, draw, text width=6em, text centered, rounded corners, minimum height=1.5em]
	\tikzstyle{hltBlock} = [rectangle, draw, text width=2em, text centered, rounded corners, font=\tiny, minimum height=1.2em]
	\tikzstyle{line} = [draw, -latex']

	% Nodes
    % HLT
    %\node (HLT) [right=0.3cm of ALICE] {\frame{\includegraphics[height=1.25cm]{images/server-farm-hi.png}}};
    % We create the structure that we want to describe, then fit a box around it.
    % Everything is positioned relative to this object.
    \begin{scope}[node distance = 0.25cm]
        \node[hltBlock] (emc1) {EMC QA 1};
        \node[hltBlock] (emc2) [right= of emc1] {EMC QA 2};
        \node[hltBlock] (tpc1) [right= of emc2] {TPC QA 1};
        \node[hltBlock] (tpc2) [right= of tpc1] {TPC QA 2};
        \node[hltBlock] (additionalNode) [right= of tpc2] {...};
        \node[hltBlock] (emcMerger) [below= 0.65cm of $(emc1)!0.5!(emc2)$] {EMC merger};
        \node[hltBlock] (tpcMerger) [below= 0.65cm of $(tpc1)!0.5!(tpc2)$] {TPC merger};
        % Position at intersection from these two nodes. See: https://tex.stackexchange.com/a/70343
        \node[hltBlock] (additionalMerger) at (tpcMerger -| additionalNode) {...};
        % Fitting of the objects the rectangle: https://tex.stackexchange.com/a/7816
        \node[rectangle, thick, draw, fit={(emc1) (tpcMerger) (additionalMerger)}] (HLT) {};
    \end{scope}
    % ALICE
    % Position relative to the HLT so everything is in the right place.
    % Can't place the ALICE image first or the box around the HLT components won't be positioned properly.
    \node [left=0.5cm of HLT] (ALICE) {\frame{\includegraphics[height=2cm]{images/{ALICE_RUN2_labels_HR}.eps}}};

    % Overwatch
    % Need to specify the distances because otherwise it will use the node distance as the hypotenuse,
    % which is shorter than we want!
    \node [block] (receivers)   [below left= 0.8cm and 0.6cm of tpcMerger] {Receivers};
    \node [block] (storage)     [below left= 1.25cm and 1cm of receivers] {Storage};
    \node [block] (processing)  [below= 1.25cm of receivers] {Processing};
    \node [block] (processingModule) [above right= 0.35cm and 0.5cm of processing] {Tasks};
    \node [block] (trendingModule) [below right= 0.35cm and 0.5cm of processing] {Trending};
    \node [block] (webApp)      [below= 1.25cm of processing] {Web App};

    % Overwatch (bak)
    % Adjustments in distance are first y, and then x (in the direction of the stated comparison point.)
    %\node [block] (receivers) [below left= 0.75cm of tpcMerger] {Receivers};
    %%\node [block] (receiver)    [below=1cm of HLT] {Receivers};
    %\node [block, xshift=-4.5cm] (storage)     [below of = receivers] {Storage};
    %%\node [block] (storage)     [below left=0.75cm and 1cm of receivers] {Storage};
    %\node [block] (processing)  [below of = receivers] {Processing};
    %\node [block, xshift=2.25cm] (processingModule) [above right of = processing] {Tasks};
    %\node [block, xshift=2.25cm] (trendingModule) [below right of = processing] {Trending};
    %\node [block] (webApp)      [below of = processing] {Web App};

    % Labels
    \node [font=\footnotesize] (labelALICE) [above=0cm of ALICE] {ALICE};
    \node [font=\footnotesize] (labelHLT)   [above=.05cm of HLT] {HLT ZMQ Subsystem};

    % Lines (with some labels)
    \path [line] (ALICE) -- (HLT);
    % HLT
    \draw[->] (emc1) -- (emcMerger);
    \draw[->] (emc2) -- (emcMerger);
    \draw[->] (tpc1) -- (tpcMerger);
    \draw[->] (tpc2) -- (tpcMerger);
    \draw[->] (additionalNode) -- (additionalMerger);
    % Mergers -> Receiver(s)
    \draw[->] (emcMerger.south) -- (receivers);
    \draw[->] (tpcMerger.south) -- (receivers);
    \draw[->] (additionalMerger.south) -- node[below right] {\small{ZeroMQ}} (receivers);
    % Receiver connections
    \path [line] (receivers) -- (storage);
    \path [line, dashed] (receivers) -- node[right] {\small{Trigger}} (processing);
    % Line options described here: https://tex.stackexchange.com/a/56591
    \draw[-latex] (processing) to[bend right=5] (storage);
    \draw[-latex] (storage) to[bend right=5] (processing);
    % Processing loop
    \draw[->] (processing) -- (processingModule);
    \draw[->] (processingModule) -- (trendingModule);
    \draw[->] (trendingModule) -- (processing);
    \node [scale=1.5] (circularArrow) [right=0.5cm of processing] {\rotatebox[origin=c]{270}{$\circlearrowright$}};
    % WebApp
    \draw[-latex] (webApp) to[bend right=5] (storage);
    \draw[-latex] (storage) to[bend right=5] (webApp);
    \draw[-latex] (webApp) to[bend right=10] node[right] {\small{slices}} (processing);
    \draw[-latex] (processing) to[bend right=10] node[left] {\small{Time}} (webApp);
    % Double arrow is a possible alternative.
    %\draw[latex'-latex',double] (webApp) -- node {\small{Time slices}} (processing);

\end{tikzpicture}
\end{center}

-->

# {.standout}

Backup

<!--

# First backup slide {.plain .noframenumbering}

- First backup topic

-->

<!--

NOTE: This was integrated into the overall diagram.

# HLT Diagram {.noframenumbering}

\begin{center}
\begin{tikzpicture}[node distance = 1.75cm, on grid]
    %\draw[help lines] (-6,-9) grid (6,1);
	\tikzstyle{qaBlock} = [rectangle, draw, text width=3.4em, text centered, rounded corners, minimum height=1.5em]
	\tikzstyle{line} = [draw, -latex']

%\draw (HLT) [right=0.3cm of ALICE] rectangle +(2cm, -2cm);
\node[qaBlock] (emc1) {\tiny{EMC QA 1}};
\node[qaBlock] (emc2) [right= of emc1] {\tiny{EMC QA 2}};
\node[qaBlock] (tpc1) [right= of emc2] {\tiny{TPC QA 1}};
\node[qaBlock] (tpc2) [right= of tpc1] {\tiny{TPC QA 2}};
\node[qaBlock] (additionalNode) [right= of tpc2, xshift=0.2cm] {\tiny{...}};
\node[qaBlock] (emcMerger) [below= 0.75cm of $(emc1)!0.5!(emc2)$] {\tiny{EMC merger}};
\node[qaBlock] (tpcMerger) [below= 0.75cm of $(tpc1)!0.5!(tpc2)$] {\tiny{TPC merger}};
\node[qaBlock] (additionalMerger) at (tpcMerger -| additionalNode) {\tiny{...}};
\node[rectangle, semithick, draw, fit={(emc1) (tpcMerger) (additionalMerger)}] (HLT) {};
\node (labelHLT) [above= of HLT] {HLT};

\draw[->] (emc1) -- (emcMerger);
\draw[->] (emc2) -- (emcMerger);
\draw[->] (tpc1) -- (tpcMerger);
\draw[->] (tpc2) -- (tpcMerger);
\draw[->] (additionalNode) -- (additionalMerger);

% The receiver
\node[below= of tpcMerger] (receivers) {Receivers};
\draw[->] (emcMerger.south) -- (receivers);
\draw[->] (tpcMerger) -- (receivers);
\draw[->] (additionalMerger.south) -- (receivers);
    %\node (HLT) [right=0.3cm of ALICE] {\frame{\includegraphics[height=1.25cm]{images/server-farm-hi.png}}};
    % Adjustments in distance are first y, and then x (in the direction of the stated comparison point.)

\end{tikzpicture}
\end{center}

-->

