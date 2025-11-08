"use client";

import React, { useState, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  MapPin, 
  Eye, 
  BookOpen, 
  Target, 
  ExternalLink,
  ZoomIn,
  FileText,
  Lightbulb,
  AlertCircle
} from 'lucide-react';

interface ErrorDetails {
  type: string;
  description: string;
  correct_answer: string;
  severity: string;
}

interface CroppedImage {
  file_id: string;
  url: string;
  coordinates: {
    x: number;
    y: number;
    w: number;
    h: number;
  };
}

interface ErrorActions {
  locate_in_original: {
    coordinates: {
      x: number;
      y: number;
      w: number;
      h: number;
    };
    description: string;
  };
  view_explanation: {
    detailed_analysis: string;
    solution_steps: string;
  };
  related_practice: {
    knowledge_points: string[];
    difficulty_level: string;
  };
}

interface ErrorCard {
  card_id: string;
  error_details: ErrorDetails;
  cropped_image: CroppedImage;
  knowledge_points: string[];
  actions: ErrorActions;
}

interface CroppedRegionGradingViewProps {
  originalImageUrl: string;
  errorCards: ErrorCard[];
  gradingSummary: {
    score: number;
    max_score: number;
    percentage: number;
    feedback: string;
    strengths: string[];
    suggestions: string[];
  };
  knowledgePointSummary: {
    total_points: number;
    points: string[];
    mastery_analysis: any;
  };
}

export default function CroppedRegionGradingView({
  originalImageUrl,
  errorCards,
  gradingSummary,
  knowledgePointSummary
}: CroppedRegionGradingViewProps) {
  const [selectedCard, setSelectedCard] = useState<ErrorCard | null>(null);
  const [showOriginalImage, setShowOriginalImage] = useState(false);
  const [highlightCoordinates, setHighlightCoordinates] = useState<any>(null);
  const [originalImageScale, setOriginalImageScale] = useState(1);
  
  const originalCanvasRef = useRef<HTMLCanvasElement>(null);
  const originalImageRef = useRef<HTMLImageElement>(null);

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'high': return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'medium': return <AlertCircle className="w-4 h-4 text-orange-500" />;
      case 'low': return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      default: return <AlertCircle className="w-4 h-4 text-red-500" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'high': return 'border-red-500 bg-red-50';
      case 'medium': return 'border-orange-500 bg-orange-50';
      case 'low': return 'border-yellow-500 bg-yellow-50';
      default: return 'border-red-500 bg-red-50';
    }
  };

  const getSeverityBadgeVariant = (severity: string) => {
    switch (severity) {
      case 'high': return 'destructive';
      case 'medium': return 'secondary';
      case 'low': return 'outline';
      default: return 'destructive';
    }
  };

  const handleLocateInOriginal = (coordinates: any) => {
    setHighlightCoordinates(coordinates);
    setShowOriginalImage(true);
    
    // Draw highlight on original image after a short delay
    setTimeout(() => {
      drawOriginalWithHighlight(coordinates);
    }, 100);
  };

  const drawOriginalWithHighlight = (coordinates: any) => {
    const canvas = originalCanvasRef.current;
    const image = originalImageRef.current;
    
    if (!canvas || !image) return;
    
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    
    // Clear and draw image
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
    
    // Draw highlight rectangle
    const x = coordinates.x * originalImageScale;
    const y = coordinates.y * originalImageScale;
    const w = coordinates.w * originalImageScale;
    const h = coordinates.h * originalImageScale;
    
    // Highlight background
    ctx.fillStyle = 'rgba(255, 0, 0, 0.2)';
    ctx.fillRect(x, y, w, h);
    
    // Highlight border
    ctx.strokeStyle = '#ef4444';
    ctx.lineWidth = 3;
    ctx.strokeRect(x, y, w, h);
    
    // Pulse effect
    ctx.shadowColor = '#ef4444';
    ctx.shadowBlur = 20;
    ctx.strokeRect(x, y, w, h);
    ctx.shadowBlur = 0;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
              <FileText className="w-5 h-5" />
              局部图批改结果
            </span>
            <Button
              variant="outline"
              onClick={() => setShowOriginalImage(true)}
            >
              <Eye className="w-4 h-4 mr-2" />
              查看原图
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4 mb-4">
            <div className="text-2xl font-bold text-primary">
              {gradingSummary.score}/{gradingSummary.max_score}
            </div>
            <div className="text-lg text-muted-foreground">
              {gradingSummary.percentage.toFixed(1)}%
            </div>
            <Badge variant={gradingSummary.percentage >= 80 ? 'default' : gradingSummary.percentage >= 60 ? 'secondary' : 'destructive'}>
              {gradingSummary.percentage >= 80 ? '优秀' : gradingSummary.percentage >= 60 ? '良好' : '需要改进'}
            </Badge>
            <div className="ml-auto text-sm text-muted-foreground">
              发现 {errorCards.length} 个需要改进的地方
            </div>
          </div>
          
          <p className="text-sm text-muted-foreground">
            {gradingSummary.feedback}
          </p>
        </CardContent>
      </Card>

      {/* Error Cards */}
      <div className="space-y-4">
        <h3 className="text-lg font-semibold">错误分析</h3>
        
        {errorCards.map((card, index) => (
          <Card 
            key={card.card_id} 
            className={`transition-all duration-200 hover:shadow-md ${getSeverityColor(card.error_details.severity)}`}
          >
            <CardContent className="p-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Cropped Image */}
                <div className="lg:col-span-1">
                  <div className="relative">
                    <img
                      src={card.cropped_image.url}
                      alt={`错误 ${index + 1}`}
                      className="w-full h-auto rounded-lg border-2 border-dashed border-gray-300"
                    />
                    <div className="absolute top-2 left-2">
                      <Badge variant={getSeverityBadgeVariant(card.error_details.severity) as any}>
                        错误 #{index + 1}
                      </Badge>
                    </div>
                    <div className="absolute top-2 right-2">
                      {getSeverityIcon(card.error_details.severity)}
                    </div>
                  </div>
                </div>
                
                {/* Error Description */}
                <div className="lg:col-span-2 space-y-4">
                  <div>
                    <h4 className="font-semibold text-lg mb-2 flex items-center gap-2">
                      {getSeverityIcon(card.error_details.severity)}
                      {card.error_details.type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                    </h4>
                    <p className="text-sm text-muted-foreground mb-3">
                      {card.error_details.description}
                    </p>
                  </div>
                  
                  {card.error_details.correct_answer && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <h5 className="font-medium text-green-800 mb-1 flex items-center gap-2">
                        <Lightbulb className="w-4 h-4" />
                        正确答案
                      </h5>
                      <p className="text-sm text-green-700">
                        {card.error_details.correct_answer}
                      </p>
                    </div>
                  )}
                  
                  {/* Knowledge Points */}
                  {card.knowledge_points.length > 0 && (
                    <div>
                      <h5 className="font-medium mb-2 flex items-center gap-2">
                        <BookOpen className="w-4 h-4" />
                        相关知识点
                      </h5>
                      <div className="flex flex-wrap gap-2">
                        {card.knowledge_points.map((point, idx) => (
                          <Badge key={idx} variant="outline">
                            {point}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Action Buttons */}
                  <div className="flex flex-wrap gap-2 pt-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => handleLocateInOriginal(card.actions.locate_in_original.coordinates)}
                    >
                      <MapPin className="w-4 h-4 mr-1" />
                      定位原图
                    </Button>
                    
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setSelectedCard(card)}
                    >
                      <ZoomIn className="w-4 h-4 mr-1" />
                      查看详解
                    </Button>
                    
                    <Button
                      size="sm"
                      variant="outline"
                    >
                      <ExternalLink className="w-4 h-4 mr-1" />
                      相关练习
                    </Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Strengths & Suggestions */}
        <Card>
          <CardHeader>
            <CardTitle>表现总结</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {gradingSummary.strengths.length > 0 && (
              <div>
                <h4 className="font-medium text-green-700 mb-2 flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  优点
                </h4>
                <ul className="text-sm space-y-1">
                  {gradingSummary.strengths.map((strength, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-green-500 mt-1">✓</span>
                      {strength}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            
            {gradingSummary.suggestions.length > 0 && (
              <div>
                <h4 className="font-medium text-amber-700 mb-2 flex items-center gap-2">
                  <span className="w-2 h-2 bg-amber-500 rounded-full"></span>
                  改进建议
                </h4>
                <ul className="text-sm space-y-1">
                  {gradingSummary.suggestions.map((suggestion, index) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-amber-500 mt-1">💡</span>
                      {suggestion}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Knowledge Point Analysis */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="w-5 h-5" />
              知识点掌握情况
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-sm">
              <span className="font-medium">涉及知识点：</span>
              <span className="ml-1">{knowledgePointSummary.total_points}个</span>
            </div>
            
            {knowledgePointSummary.mastery_analysis?.weak_areas?.length > 0 && (
              <div>
                <h4 className="font-medium text-red-700 mb-2">需要加强</h4>
                <div className="space-y-2">
                  {knowledgePointSummary.mastery_analysis.weak_areas.map((area: any, index: number) => (
                    <div key={index} className="flex items-center justify-between p-2 bg-red-50 rounded">
                      <span className="text-sm">{area.knowledge_point}</span>
                      <Badge variant={area.severity === 'high' ? 'destructive' : 'secondary'}>
                        {area.error_count}处错误
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>
            )}
            
            {knowledgePointSummary.mastery_analysis?.recommendations?.length > 0 && (
              <div>
                <h4 className="font-medium text-blue-700 mb-2">学习建议</h4>
                <ul className="text-sm space-y-1">
                  {knowledgePointSummary.mastery_analysis.recommendations.map((rec: string, index: number) => (
                    <li key={index} className="flex items-start gap-2">
                      <span className="text-blue-500 mt-1">📚</span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Original Image Dialog */}
      <Dialog open={showOriginalImage} onOpenChange={setShowOriginalImage}>
        <DialogContent className="max-w-4xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle>原图查看</DialogTitle>
          </DialogHeader>
          <div className="relative">
            <img
              ref={originalImageRef}
              src={originalImageUrl}
              alt="原始作业图片"
              className="hidden"
              onLoad={() => {
                const img = originalImageRef.current;
                const canvas = originalCanvasRef.current;
                if (img && canvas) {
                  canvas.width = img.naturalWidth;
                  canvas.height = img.naturalHeight;
                  setOriginalImageScale(Math.min(800 / img.naturalWidth, 600 / img.naturalHeight));
                  if (highlightCoordinates) {
                    drawOriginalWithHighlight(highlightCoordinates);
                  }
                }
              }}
            />
            <canvas
              ref={originalCanvasRef}
              className="w-full h-auto max-h-[70vh] object-contain"
            />
            {highlightCoordinates && (
              <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur rounded-lg p-2">
                <p className="text-sm font-medium text-red-600">已定位错误区域</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Error Detail Dialog */}
      <Dialog open={!!selectedCard} onOpenChange={() => setSelectedCard(null)}>
        <DialogContent className="max-w-2xl">
          {selectedCard && (
            <>
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  {getSeverityIcon(selectedCard.error_details.severity)}
                  详细分析
                </DialogTitle>
              </DialogHeader>
              <ScrollArea className="max-h-[60vh]">
                <div className="space-y-4 pr-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <img
                        src={selectedCard.cropped_image.url}
                        alt="错误区域"
                        className="w-full h-auto rounded-lg border"
                      />
                    </div>
                    <div className="space-y-3">
                      <div>
                        <h4 className="font-medium mb-1">错误类型</h4>
                        <p className="text-sm text-muted-foreground">
                          {selectedCard.error_details.type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                        </p>
                      </div>
                      <div>
                        <h4 className="font-medium mb-1">错误描述</h4>
                        <p className="text-sm text-muted-foreground">
                          {selectedCard.error_details.description}
                        </p>
                      </div>
                    </div>
                  </div>
                  
                  {selectedCard.actions.view_explanation.detailed_analysis && (
                    <div>
                      <h4 className="font-medium mb-2">详细分析</h4>
                      <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                        <p className="text-sm text-blue-800">
                          {selectedCard.actions.view_explanation.detailed_analysis}
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {selectedCard.actions.view_explanation.solution_steps && (
                    <div>
                      <h4 className="font-medium mb-2">解题步骤</h4>
                      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                        <p className="text-sm text-green-800 whitespace-pre-line">
                          {selectedCard.actions.view_explanation.solution_steps}
                        </p>
                      </div>
                    </div>
                  )}
                  
                  {selectedCard.knowledge_points.length > 0 && (
                    <div>
                      <h4 className="font-medium mb-2">相关知识点</h4>
                      <div className="flex flex-wrap gap-2">
                        {selectedCard.knowledge_points.map((point, index) => (
                          <Badge key={index} variant="outline">
                            {point}
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </ScrollArea>
              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button variant="outline" onClick={() => setSelectedCard(null)}>
                  关闭
                </Button>
                <Button>
                  生成专项练习
                </Button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}