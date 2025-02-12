# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
"""Prompt templates for the LLM Comparator script."""            

DEFAULT_LLM_JUDGE_PROMPT_TEMPLATE = """

### **Prompt del Giudice LLM con Attività di Tagging**

**Compito:**
Sei un Giudice LLM incaricato di valutare una risposta (A) data una domanda (Q) e una risposta di riferimento (GTA).

**Regole di Valutazione:**
1. **A e GTA corrispondono perfettamente nel significato (possono essere formulate diversamente):**
   Verdetto: `Correct`
   Spiegazione: Spiega perché A e GTA corrispondono nel significato.

2. **A e GTA sono diversi:**
   Verdetto: `Wrong`
   Spiegazione: Spiega perché A e GTA differiscono.

3. **A fornisce una risposta incompleta:**
   Verdetto: `Incomplete`
   Spiegazione: Spiega perché A è incomplete.
   
4. **A aggiunge informazioni rispetto a GTA:**
   Verdetto: `Inference`
   Spiegazione: Spiega quali informazioni aggiunge A rispetto a GTA.

5. **A è "domanda saltata" (il modello ha saltato la domanda):**
   Verdetto: `Skipped Question`
   Spiegazione: Indica che A è assente, il modello non ha fornito alcuna risposta..

6. **A è N/A mentre GTA contiene una risposta:**
   Verdetto: `Missing Answer`
   Spiegazione: Indica che A è mancante mentre GTA fornisce una risposta.



**Formato di Output:**
Presenta la tua valutazione nel seguente formato XML:
```xml
<result>
  <explanation>LA TUA SPIEGAZIONE QUI.</explanation>
  <verdict>UNO DEI VERDETTI QUI.</verdict>
</result>
```

**Opzioni di Verdetto:**
Il verdetto deve essere uno dei seguenti:
['Correct', 'Wrong', 'Skipped Question', 'Missing Answer', 'Incomplete', 'Inference']

---

**Esempi:**

**Esempio 1:**
Q: Che lavoro faceva il richiedente?
A: Cuoco
GTA: lavorava come cuoco

```xml
<result>
  <explanation>A e GTA hanno lo stesso significato.</explanation>
  <verdict>Correct</verdict>
</result>
```

**Esempio 2:**
Q: Quanti figli aveva il richiedente?
A: risposta mancante
GTA: 2

```xml
<result>
  <explanation>A è "domanda saltata", il modello ha saltato la domanda.</explanation>
  <verdict>Skipped Question</verdict>
</result>
```

**Esempio 3:**
Q: Qual è il nome della moglie del richiedente?
A: Maria
GTA: Anna

```xml
<result>
  <explanation>A e GTA sono diversi.</explanation>
  <verdict>Wrong</verdict>
</result>
```

**Esempio 4:**
Q: Quanti anni ha il richiedente?
A: N/A
GTA: 35

```xml
<result>
  <explanation>A è N/A mentre GTA fornisce una risposta.</explanation>
  <verdict>Missing Answer</verdict>
</result>
```

**Esempio 5:**
Q: Perché la commissione non ritiene credibile la dichiarazione?
A: Per via delle contraddizioni.
GTA: Perché il richiedente si contraddice più volte descrivendo la sua fuga, menzionando di essere andato in Grecia, ma al tempo stesso di aver preso un barcone in Libia. 

```xml
<result>
  <explanation>A risponde solo parzialmente alla domanda.</explanation>
  <verdict>Incomplete</verdict>
</result>
```

**Esempio 6:**
Q: Che paesi ha visitato il richiedente?
A: Sudan, Libia, Algeria.
GTA: Sudan, Libia.

```xml
<result>
  <explanation>A aggiunge informazioni rispetto a GTA.</explanation>
  <verdict>Inference</verdict>
</result>
```

---

**Il Tuo Compito:**
Valuta la seguente Q, A e GTA secondo le regole sopra indicate. Fornisci il tuo output nel formato XML specificato.

Q: {prompt}
A: {response_a}
GTA: {response_b}

"""

DEFAULT_LLM_JUDGE_WITH_REFERENCE_PROMPT_TEMPLATE = """
### **Prompt del Giudice LLM con Attività di Tagging**

**Compito:**
Sei un Giudice LLM incaricato di valutare una risposta (A) data una domanda (Q), una risposta di riferimento (GTA) e il testo (RT) usato per formulare la risposta.

**Regole di Valutazione:**
1. **A e GTA sono entrambi N/A:**
   Verdetto: `True Negative`
   Spiegazione: Indica che sia A che GTA sono N/A (compresi "Sì" o "No").
   
2. **A contiene una risposta mentre GTA è N/A e, considerando RT, A è inventata:**  
   Verdetto: `Hallucination`  
   Spiegazione: Indica che A fornisce una risposta (compresi "Sì" o "No"), che non ha riscontro in RT.  

3. **A contiene una risposta mentre GTA è N/A e, considerando RT, A è stata inferta da RT.**  
   Verdetto: `Inference`  
   Spiegazione: Indica che A fornisce una risposta (compresi "Sì" o "No"), che è stata inferta da RT. 

To differentiate between Inference and Hallucination follow this line of thought: 
- Does RT contain any clues, even if indirect, that would allow a reader to reasonably infer the answer? 
-- If yes, label that answer as an inference.
- Is the answer introducing details that have no trace whatsoever in RT? 
-- If yes, mark that answer as a hallucination.

**Formato di Output:**
Presenta la tua valutazione nel seguente formato XML:
```xml
<result>
  <explanation>LA TUA SPIEGAZIONE QUI.</explanation>
  <verdict>UNO DEI VERDETTI QUI.</verdict>
</result>
```

**Opzioni di Verdetto:**
Il verdetto deve essere uno dei seguenti:
['True Negative', 'Hallucination', 'Inference']

---
**Esempi:**

**Esempio 1:**
Q: Il richiedente è andato a scuola?
A: N/A
GTA: N/A
RT: N/A

```xml
<result>
  <explanation>A e GTA sono entrambe N/A.</explanation>
  <verdict>True Negative</verdict>
</result>
```

**Esempio 2:**
Q: Dove dimora il richiedente? 
A: Bamako
GTA: N/A
RT: Poi un giorno sono uscito, avevo fatto delle fotocopie dei miei documenti (carta d'identità, passaporto scaduto). Mentre ero fuori, la polizia è andata a casa di Djibril Follana per cercarmi. Se mi avessero visto mi avrebbero ucciso. Poi Djibril Fofana mi ha chiamato e mi ha spiegato che la polizia mi cercava per uccidermi. A quel punto sono scappato e sono andato a Bamako.

```xml
<result>
  <explanation>A è stata dedotta da RT, viene menzionato il fatto che "sono andato a Bamako", ma non che dimora lì. </explanation>
  <verdict>Inference</verdict>
</result>
```

**Esempio 3:**
Q: Che lavoro svolgono o svolgevano i familiari del richiedente?
A: I genitori facevano i pastori, mentre il fratello il fabbro.
GTA: N/A
RT: Il richiedente ricorda di essere nato e cresciuto a Trantimou, Regione di Kayes, Mali, e di aver lavorato come cuoco. Ricorda di avere due fratelli, uno più grande e uno più piccolo, e di non essere sposato né avere figli. Ricorda di aver frequentato la scuola fino all'età di 8 anni. Ricorda di aver vissuto in Gabon per un anno e tre mesi, lavorando come muratore, e di aver litigato con suo fratello per motivi economici. 
```xml
<result>
  <explanation>A non trova riscontro in RT, è stata inventata. </explanation>
  <verdict>Hallucination</verdict>
</result>
```

---

**Il Tuo Compito:**
Valuta la seguente Q, A, RT e GTA secondo le regole sopra indicate. Fornisci il tuo output nel formato XML specificato.

Q: {prompt}
A: {response_a}
RT: {text_reference}
GTA: {response_b}

"""

