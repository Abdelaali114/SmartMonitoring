import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpDownloadProgressEvent, HttpEventType } from '@angular/common/http';
import { MarkdownComponent } from 'ngx-markdown';
import { CommonModule } from '@angular/common';

interface ChatEntry {
  question: string;
  answer: string;
}

@Component({
  selector: 'app-chat',
  imports: [FormsModule, MarkdownComponent ,CommonModule],
  templateUrl: './chat.component.html',
  styleUrl: './chat.component.css'
})
export class ChatComponent {
  
  query: string = "";
  response: any;
  progress: boolean = false;

  // 🧠 Store history of Q&A
  history: ChatEntry[] = [];

  constructor(private http: HttpClient) {}

  askAgent() {
    if (!this.query.trim()) return;

    const currentQuestion = this.query;
    this.response = "";
    this.progress = true;

    // hanaya localhost
    this.http.get("http://localhost:8888/AskAgent?query=" + this.query,
      { responseType: 'text', observe: 'events', reportProgress: true })
      .subscribe({
        next: evt => {
          if (evt.type === HttpEventType.DownloadProgress) {
            this.response = (evt as HttpDownloadProgressEvent).partialText;
          }
        },
        error: err => {
          this.progress = false;
          this.history.push({ question: currentQuestion, answer: "❌ Error: " + err.message });
        },
        complete: () => {
          this.progress = false;
          // ✅ Add the Q&A to history
          this.history.push({ question: currentQuestion, answer: this.response });
          this.query = ""; // clear input
        }
      });
  }
}
